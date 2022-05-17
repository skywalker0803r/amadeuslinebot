import pandas as pd
import pandas_datareader.data as web
import datetime
import warnings
from stocker import Stocker
warnings.filterwarnings('ignore')

start = datetime.datetime(2010, 1, 1)
end = datetime.datetime.now()

def predict_line_graph(sid):
	df_Close=web.DataReader(sid+'.tw','yahoo',start,end)['Close']
	target=Stocker(df_Close.squeeze())
	fig=target.create_prophet_model(sid=sid,days=90)
	fig.savefig('./images/'+sid+'_fbprop'+'.png')
