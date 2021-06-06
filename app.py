import csv
from datetime import datetime, timedelta
import calendar
from logging import PlaceHolder
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
from pandas import DataFrame
from streamlit.config import _server_run_on_save

fileName='rel.csv'

@st.cache
def get_data():
    data=pd.read_csv(fileName,index_col=0, parse_dates=['Date'])
    return data
    
def min_max():
    data=get_data()
    low=min(data['Date'])
    hi=max(data['Date'])
    return (low,hi)

def float_range(start, stop, step):
    while start < stop:
        yield float(start)
        start += float(step)

def filter_data(startDate,endDate):
    data=get_data()
    #targetData=list(filter(lambda x:x['Date']>startDate and x['Date']<endDate,data[1:]))
    targetData=data.loc[(data['Date']>startDate) & (data['Date']<endDate)]
    return targetData

def show_data(data):
    if len(data) < 1:
        st.write('NA')
        return
    #Data preview
    dates=data['Date'].values
    openPrice=data['Open Price'].values
    closePrice=data['Close Price'].values
    highPrice=data['High Price'].values
    lowPrice=data['Low Price'].values
    x=dates
    y=openPrice
    fig,ax=plt.subplots()
    fig.set_size_inches(15, 8)
    #ax.set_title(data[0]['Symbol'],fontsize=24)
    ax.set_title(data.index[0],fontsize=24)
    ax.set_xlabel('Time',fontsize=14)
    ax.set_ylabel('Price',fontsize=14)
    ax.plot(x,y,linewidth=3)
    #ax.plot(x,closePrice,linewidth=3,ls='--')
    ax.plot(x,highPrice,linewidth=3,c='red',ls='--')
    ax.plot(x,lowPrice,linewidth=3,c='blue',ls='--')
    for i in float_range(grid_lower,grid_upper,grid_gap):
        ax.axhline(y=i,c='red',ls='--')     
    st.pyplot(fig)

st.write('# Grid Bot Simulator')
date_min_max=min_max()
st.sidebar.write('#### Select date range')
sDate=st.sidebar.date_input('Start date',date_min_max[0])
eDate=st.sidebar.date_input('End date',date_min_max[1])

show_full_data=st.checkbox('Full data')
if show_full_data:
    st.write('Full data')
    data=get_data()
    st.dataframe(data)
    st.write(f'Total records {len(data)}')

my_time = datetime.min.time()
s_datetime = datetime.combine(sDate, my_time)
e_datetime = datetime.combine(eDate, my_time)
filteredData=filter_data(s_datetime,e_datetime)

show_filtered_data=st.checkbox('Filtered data',value=True)
if show_filtered_data:
    st.write('Filtered data')
    st.dataframe(filteredData)
    st.write(f'Total records {len(filteredData)} filtered between {sDate.strftime("%b %d %Y")} and {eDate.strftime("%b %d %Y")}')

grid_lower=st.sidebar.number_input('Grid lower value',value=1900)
grid_upper=st.sidebar.number_input('Grid upper value',value=2100)
grid_gap=st.sidebar.number_input('Grid gap value',value=10)

show_filtered_data_graph=st.checkbox('Show filtered data graph',value=False)
if show_filtered_data_graph:
    st.write('Filtered data spread')
    show_data(filteredData)

trade_quantity=st.sidebar.number_input('Trade quanity',1,value=10)
start_cash=st.sidebar.number_input('Start cash',1,value=200000)

#Remaining cash
remCash=start_cash
#Current stock quanity
currStocks=0
#trade quanitiy
tQ=trade_quantity
#lower limit
gL=grid_lower
#upper limit
gU=grid_upper
#Grid gap 
gG=grid_gap


def place_orders(cP):
    global remCash,currStocks
    if(cP<gL or cP>gU):
        print('Exiting trade as price is outside the grid')
        return
    
    #Put buy orders below current price
    refBuyPrice=gL+((cP-gL)//gG)*gG
    for i in range(1,2):
        tStamp=datetime.now()
        buyPrice=refBuyPrice-i*gG
        if(buyPrice<gL):
            print(f'Exiting trade as range is outside the grid @ {datetime.now()}')
            return
        cashRequired=tQ*buyPrice
        print(f'gridMatchPrice={refBuyPrice} buyPrice={buyPrice} cashRequired={cashRequired} @{tStamp}')
        if(remCash>cashRequired):
            orders.append({'type':'BUY','quantity':tQ,'price':buyPrice,'timeStamp':str(tStamp)})
            remCash=remCash-cashRequired
            print(f'Added buy @{buyPrice} remainingCash={remCash} @{tStamp}')
        else:
            print(f'Out of cash for lot buy. Cash left={remCash} @{tStamp}')

    #Put sell orders above current price 
    if(currStocks<tQ):
        print(f'Exiting as not enough stocks to trade. currentStocks={currStocks} @ {datetime.now()}')
        return
    refSellPrice=gU-((gU-cP)//gG)*gG
    
    for i in range(1,2):
        tStamp=datetime.now()
        sellPrice=refSellPrice+i*gG
        if(sellPrice>gU):
            print(f'Exiting trade as range is outside the grid @ {datetime.now()}')
            return
        potentialEarnings=tQ*sellPrice
        print(f'gridMatchPrice={refSellPrice} sellPrice={sellPrice} *earnings={potentialEarnings} @{tStamp}')
        if(currStocks>=tQ):
            orders.append({'type':'SELL','quantity':tQ,'price':sellPrice,'timeStamp':str(tStamp)})
            currStocks=currStocks-tQ
            print(f'Added sell @{sellPrice} remainingStocks={currStocks} @{tStamp}')
        else:
            print(f'Waiting as less than lot stocks to trade @{tStamp}')


def process_orders(ohlc):
    global remCash,currStocks
    for o in orders:
        if(o.get('status','')=='Executed'):
            return
        tradePrice=o['price']
        quantity=o['quantity']
        orderType=o['type']
        if(tradePrice>=float(ohlc['Low Price']) and tradePrice<=float(ohlc['High Price'])):
            o['status']='Executed'
            if(orderType=='BUY'):
                currStocks=currStocks+quantity
            else:
                currStocks=currStocks-quantity
                remCash=remCash+tradePrice*quantity
            print(f'Order type={orderType} processed for price={tradePrice}')
        else:
            print(f'Order type={orderType} for price={tradePrice} not processed')


def clear_pending_orders():
    global remCash,currStocks,orders,pastOrders
    for o in orders:
        #pastOrders.append(o)
        if(o.get('status','')!='Executed'):
            if(o['type']=='BUY'):
                remCash=remCash+o['quantity']*o['price']
            else:
                currStocks=currStocks+o['quantity']
    orders=[]


def get_trades(b,s,status):
    for i,po in enumerate(pastOrders):
        for o in po:
            if o.get('status','')==status:
                continue
            if(o.get('type','')=='BUY'):
                b.append((i,o['price']))
            else:
                s.append((i,o.get('price',0)))


#Run on prices
#Orders
orders=[]
#Past orders
pastOrders=[]
for i,o in filteredData.iterrows():
    place_orders(o['Open Price'])
    process_orders(o)
    #processOrders({'Low':o['Low'],'High':o['High']})
    pastOrders.append(orders)
    clear_pending_orders()
    #print(f'{i} in {o}')


def show_bot_run():
    if len(filteredData) <1:
        st.write('NA')
        return
    #bot buy \ sell orders
    bo=[]
    so=[]
    get_trades(bo,so,'')
    #trade buy \ sell executions
    tb=[]
    ts=[]
    get_trades(tb,ts,'Executed')
    fig,ax=plt.subplots()
    fig.set_size_inches(15, 8)
    dates=filteredData['Date'].values
    openPrice=filteredData['Open Price'].values
    highPrice=filteredData['High Price'].values
    lowPrice=filteredData['Low Price'].values
    x=dates
    y=openPrice
    ax.set_title(filteredData.index[0],fontsize=24)
    ax.set_xlabel('Time',fontsize=14)
    ax.set_ylabel('Price',fontsize=14)
    td=timedelta(hours=1)
    for b in bo:
        ax.scatter(dates[b[0]],b[1],c='orange',alpha=.5,s=200)
    for s in so:
        ax.scatter(dates[s[0]],s[1],marker='^',c='blue',alpha=.5,s=200)

    for b in tb:
        ax.scatter(dates[b[0]],b[1],c='green',alpha=.5,s=200)
    for s in ts:
        ax.scatter(dates[s[0]],s[1],marker='^',c='red',alpha=.5,s=200)    

    ax.plot(x,y,linewidth=3)
    for i in float_range(gL,gU,gG):
        ax.axhline(y=i,c='grey',ls='dotted')
    #add legend
    plt.scatter([], [], c='orange',s=200,label='Bot buy bid')    
    plt.scatter([], [], c='blue', marker='^',s=200,label='Bot sell bid')    
    plt.scatter([], [], c='green', s=200,label='Buy executed')    
    plt.scatter([], [], c='red', marker='^',s=200,label='Sell executed')    
    plt.legend(scatterpoints=1, frameon=False, labelspacing=1, title='Legend')
    ax.plot(x,highPrice,linewidth=3,c='pink',ls='--')
    ax.plot(x,lowPrice,linewidth=3,c='blue',ls='--')
    #ax.tick_params(axis='x', rotation=30)
    st.pyplot(fig)

st.write('### Bot run output')
show_bot_run()

st.write('#')
show_trades=st.checkbox('Show trades',value=False)

if show_trades:
    if len(pastOrders)<1:
        st.write('NA')
    else:    
        all_orders=list(filter(lambda x:x.get('status','')=='Executed',[o for p in pastOrders for o in p]))
        df=DataFrame(all_orders)
        b=0
        b_c=0
        s=0
        s_c=0
        for o in all_orders:
            value=o['price']*o['quantity']
            if o['type']=='BUY':
                b=b+value
                b_c+=1
            else:
                s=s+value
                s_c+=1
        st.dataframe(df[['type','quantity','price']])
        st.write(f'Amount buy={b} sell={s}')
        st.write(f'Amount delta={abs(b-s)}')
        st.write(f'Count buys={b_c} vs sells={s_c}')
