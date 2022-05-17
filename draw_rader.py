#忽略錯誤訊息
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

#月轉季函數
def toSeasonal(df):
    season4 = df[df.index.month == 3]
    season1 = df[df.index.month == 5]
    season2 = df[df.index.month == 8]
    season3 = df[df.index.month == 11]

    season1.index = season1.index.year
    season2.index = season2.index.year
    season3.index = season3.index.year
    season4.index = season4.index.year - 1

    newseason1 = season1
    newseason2 = season2 - season1.reindex_like(season2)
    newseason3 = season3 - season2.reindex_like(season3)
    newseason4 = season4 - season3.reindex_like(season4)

    newseason1.index = pd.to_datetime(newseason1.index.astype(str) + '-05-15')
    newseason2.index = pd.to_datetime(newseason2.index.astype(str) + '-08-14')
    newseason3.index = pd.to_datetime(newseason3.index.astype(str) + '-11-14')
    newseason4.index = pd.to_datetime((newseason4.index + 1).astype(str) + '-03-31')

    return newseason1.append(newseason2).append(newseason3).append(newseason4).sort_index()

#設定影響股價的因子
def Setfeature(data,sid):

    #特徵 1 市值=總股數*股價=(股本*1000)/10 * 股價
    股本 = data.get_by_sid('股本合計',1,sid)
    price = data.get_by_sid('收盤價', 200,sid)
    當天股價 = price[:股本.index[-1]].iloc[-1]
    當天股本 = 股本.iloc[-1]
    市值 = 當天股本 * 當天股價 / 10 * 1000

    #特徵 2 自由現金流 = 最近四季的平均自由現金流   
    df1 = toSeasonal(data.get_by_sid('投資活動之淨現金流入（流出）', 5,sid))
    df2 = toSeasonal(data.get_by_sid('營業活動之淨現金流入（流出）', 5,sid))
    自由現金流 = (df1 + df2).iloc[-4:].mean()

    #特徵3 股東權益報酬率 = 稅後淨利/權益總計      
    稅後淨利 = data.get_by_sid('本期淨利（淨損）', 1,sid)
    權益總計 = data.get_by_sid('權益總計', 1,sid)
    權益總額 = data.get_by_sid('權益總額', 1,sid)
    權益總計.fillna(權益總額, inplace=True)
    股東權益報酬率 = 稅後淨利.iloc[-1] / 權益總計.iloc[-1]

    #特徵4 營業利益成長率 = [(最新一季營業利益/去年同期營業利益)-1] * 100   
    營業利益 = data.get_by_sid('營業利益（損失）', 5,sid)
    營業利益成長率 = (營業利益.iloc[-1] / 營業利益.iloc[-5] - 1) * 100

    #特徵5 市值營收比 = 市值/當季營收(最近四個月營收的總和)   
    當月營收 = data.get_by_sid('當月營收', 4,sid) * 1000
    當季營收 = 當月營收.iloc[-4:].sum()
    市值營收比 = 市值 / 當季營收

    #特徵6 RSV = (股價-最近150日最小值) / (最近150日最大值-最近150日最小值) 
    RSV = (price.iloc[-1] - price.iloc[-150:].min()) / (price.iloc[-150:].max() - price.iloc[-150:].min())
    
    #特徵7 本益比 = 本益比低於12算便宜
    本益比 = data.get_by_sid('本益比',1,sid).iloc[-1]
    
    #特徵8 股價淨值比 = 股價/淨值
    淨值 = data.get_by_sid('資產總計',1,sid) - data.get_by_sid('負債總計',1,sid)
    每股淨值 = 淨值/股本
    股價淨值比 = (當天股價/每股淨值)/10
    股價淨值比 = 股價淨值比.iloc[-1]
    
    
    return [當天股價,市值,自由現金流,股東權益報酬率,營業利益成長率,市值營收比,RSV,本益比,股價淨值比]

#低品質分界點
def q_L(col):
    d={'營業利益成長率': -67.5993513089137, '市值': 2483027091.2500005, '市值營收比': 2.048592873716654, '本益比': 7.4825, '股東權益報酬率': 0.0011606901373642112, 'RSV': 0.235442356625563, '自由現金流': -45446.75, '股價淨值比': 0.7844525846892566}
    col=col.name
    return d[col]
#中等品質分界
def q_M(col):
    d={'營業利益成長率': -15.631107158883623, '市值': 5751672225.0, '市值營收比': 3.475890150535416, '本益比': 13.184999999999999, '股東權益報酬率': 0.012937804321485849, 'RSV': 0.48756142506142514, '自由現金流': 28149.5, '股價淨值比': 1.1358825510051496}
    col=col.name
    return d[col]
#高品質分界
def q_H(col):
    d={'營業利益成長率': 22.71437960605664, '市值': 13876736500.0, '市值營收比': 6.158298337540723, '本益比': 21.150000000000002, '股東權益報酬率': 0.026904514328356097, 'RSV': 0.7294619746086526, '自由現金流': 168362.5, '股價淨值比': 1.7427073075251815}
    col=col.name
    return d[col]



#轉換函數
def trans(df):
    return df.apply(lambda s: 4 if s>q_H(df) 
            else 3 if q_H(df)>s>q_M(df) 
            else 2 if q_M(df)>s>q_L(df) 
            else 1)

def generate_df(sid,data):
    df = pd.DataFrame()
    temp = Setfeature(data,sid)
    df['市值'] = temp[1]
    df['自由現金流'] = temp[2]
    df['股東權益報酬率'] = temp[3]
    df['營業利益成長率'] = temp[4]
    df['市值營收比'] = temp[5]
    df['RSV'] = temp[6]
    df['本益比'] = temp[7]
    df['股價淨值比'] = temp[8]
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()
    df = df.reset_index()
    #欄位數值類別化轉換
    for col in df.columns[1:].tolist():
        df[col]=trans(df[col])
    return df

#繪圖
import matplotlib.pyplot as plt
def result_pic(sid,result):
    labels = result.columns[1:].tolist()
    kind = result['stock_id'].values[0]

    # 由于在雷达图中，要保证数据闭合，这里就再添加L列，并转换为 np.ndarray
    result = pd.concat([result.iloc[:,1:], result[['市值']]], axis=1)
    centers = np.array(result)[0]

    # 分割圆周长，并让其闭合
    n = len(labels)
    angle = np.linspace(0, 2 * np.pi, n, endpoint=False)
    angle = np.concatenate((angle, [angle[0]]))

    # 画线
    fig = plt.figure(figsize=(5,5))
    ax = fig.add_subplot(111,polar=True)
    ax.plot(angle, centers, linewidth=2, label=kind)
    ax.fill(angle, centers)  # 填充底色
    ax.set_thetagrids(angle * 180 / np.pi, labels)
    plt.title(kind)
    plt.savefig('./images/'+sid+'.png')

def pie_graph(sid):
    #載入data
    from finlab.data import Data
    data = Data()
    #產生df
    df=generate_df(sid,data)
    #中文字型
    from matplotlib.font_manager import FontProperties
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei'] 
    plt.rcParams['axes.unicode_minus'] = False
    #把df丟給繪圖器
    result_pic(sid,df)

