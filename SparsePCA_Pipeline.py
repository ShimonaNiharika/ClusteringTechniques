import numpy as np
from time import time
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
plt.ioff()
import sys,glob,os
from pcp_outliers import pcp
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d import proj3d
from sklearn import metrics
from sklearn.decomposition import PCA,MiniBatchSparsePCA,RandomizedPCA
from sklearn.kernel_ridge import KernelRidge
from sklearn.svm import SVC,SVR
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error,explained_variance_score,mean_absolute_error,r2_score,make_scorer
from sklearn.model_selection import GridSearchCV, cross_val_score, KFold
from pylab import * 
import scipy.io as sio
import pandas as pd
from sklearn.cluster import KMeans,SpectralClustering

def Split_class():
	"Splits the dataset into Autism and Controls"

	Location = r'/home/niharika-shimona/Documents/Projects/Autism_Network/Data/matched_data.xlsx'
	df = pd.read_excel(Location,0)
	mask_cont = df['Primary_Dx'] == 'None' 
	mask_aut = df['Primary_Dx'] != 'None' 

 	df_cont = df[mask_cont]
 	df_aut = df[mask_aut]
	
	return df_aut,df_cont
def plot_embedding(X,y, title=None):
    x_min, x_max = np.min(X, 0), np.max(X, 0)
    X = (X - x_min) / (x_max - x_min)

    fig= plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    for i in range(X.shape[0]):
        ax.scatter(X[i, 0], X[i, 1],X[i,2], color=plt.cm.Set1(y[i] / 10.))
    plt.xticks([]), plt.yticks([])
    if title is not None:
        plt.title(title)
    return fig,ax

def create_dataset(df_aut,df_cont,task,folder):
	"Creates the dataset according to classification/Clustering or regression"

	if task == 'Classification':
		for ID_NO in df_cont['ID']:

			filename = folder + '/Corr_' + `ID_NO` + '.mat'
			data = sio.loadmat(filename) 
			x_cont = data['corr']

		y_cont = np.zeros((x_cont.shape[0],1))

		for ID_NO in df_aut['ID']:

			filename = folder + '/Corr_' + `ID_NO` + '.mat'
			data = sio.loadmat(filename) 
			x_aut = data['corr']

		y_aut = np.ones((x_aut.shape[0],1))
			
	else:
		
		y_aut = np.zeros((1,1))
		y_cont = np.zeros((1,1))
		x_cont = np.zeros((1,6670))
		x_aut = np.zeros((1,6670))

        df_aut = df_aut[df_aut[task]< 7000]
    	df_cont = df_cont[df_cont[task]< 7000]

    	for ID_NO,score in zip(df_aut['ID'],df_aut[task]):

				filename = folder + '/Corr_' + `ID_NO` + '.mat'
				data = sio.loadmat(filename) 
				x_aut = np.concatenate((x_aut,data['corr']),axis =0)
				y_aut = np.concatenate((y_aut,score*np.ones((1,1))),axis =0)
		
        if (task!= 'ADOS.Total'):
			
			for ID_NO,score in zip(df_cont['ID'],df_cont[task]):

				filename = folder + '/Corr_' + `ID_NO` + '.mat'
				data = sio.loadmat(filename) 
				x_cont = np.concatenate((x_cont,data['corr']),axis =0)
				y_cont = np.concatenate((y_cont,score*np.ones((1,1))),axis =0)
			

	return x_aut[1:,:],y_aut[1:,:],x_cont[1:,:],y_cont[1:,:]

if __name__ == '__main__':

	df_aut,df_cont = Split_class()
	x_aut,y_aut,x_cont,y_cont = create_dataset(df_aut,df_cont,'bytSrsPSocTotSrsRaw','/home/niharika-shimona/Documents/Projects/Autism_Network/code/patient_data')	
	x =np.concatenate((x_cont,x_aut),axis =0)
	y =np.ravel(np.concatenate((np.zeros((x_cont.shape[0],1)),np.ones((x_aut.shape[0],1))),axis =0))	
	L,E,(u,s,v) = pcp(x.T, maxiter=1000, verbose=True, svd_method="exact")
	E = E.T
	L = L.T
	pca = PCA(svd_solver ='arpack')
	svr_poly = SVR(kernel ='rbf')
	spca_svr = Pipeline([('svr', svr_poly)])
	my_scorer = make_scorer(mean_absolute_error)

	model  =[] 
	nested_scores =[]
	ridge_range = np.linspace(0,1,3)
	c_range = np.logspace(1,6,6)
	n_comp = np.asarray(np.linspace(20,40,5),dtype = 'int8')
	p_grid = dict(svr__C =c_range)

	for i in range(5):
		inner_cv = KFold(n_splits=10, shuffle=True, random_state=i)
		outer_cv = KFold(n_splits=10, shuffle=True, random_state=i)

		clf = GridSearchCV(estimator=spca_svr, param_grid=p_grid, scoring =my_scorer,  cv=inner_cv)
		clf.fit(E,y)

		print clf.best_score_
		print clf.best_estimator_
		print '\n'
		model.append(clf.best_estimator_)

		nested_score = cross_val_score(clf, X=E, y=y, cv=outer_cv,scoring =my_scorer)
		print nested_score.mean()
		nested_scores.append(nested_score.mean())
		print 'hi'

	m = nested_scores.index(max(nested_scores))
	final_model = model[m]
 	i =0

	sPCA_MAE =[]
	sPCA_r2=[]
	sPCA_exp=[]
	sPCA_MAE_test=[]
	sPCA_r2_test =[]
	sPCA_exp_test=[]
	sys.stdout=open('results'+'.txt',"w")
	
	for train, test in inner_cv.split(E,y):

		sPCA_MAE.append(mean_absolute_error(y[train], final_model.predict(x[train])))
		sPCA_r2.append(r2_score(y[train], final_model.predict(x[train]), multioutput='variance_weighted'))
		sPCA_exp.append(explained_variance_score(y[train], final_model.predict(x[train]), multioutput='variance_weighted'))
		i= i+1
		print 'Split', i ,'\n' 
		print 'MAE : ', mean_squared_error(y[train], final_model.predict(x[train]))
		print 'Explained Variance Score : ', explained_variance_score(y[train], final_model.predict(x[train]))
		print 'r2 score: ' , r2_score(y[train], final_model.predict(x[train]))
		fig, ax = plt.subplots()
		ax.scatter(y[train],final_model.predict(x[train]),y[train])
		ax.plot([y[train].min(), y[train].max()], [y[train].min(), y[train].max()], 'k--', lw=4)
		ax.set_xlabel('Predicted')
		ax.set_ylabel('Measured')
		
		name = 'fig_'+ `i`+ '_train.png'
		fig.savefig(name)   # save the figure to fil
		plt.close(fig)

		sPCA_MAE_test.append(mean_absolute_error(y[test], final_model.predict(x[test])))
		sPCA_r2_test.append(r2_score(y[test], final_model.predict(x[test]), multioutput='variance_weighted'))
		sPCA_exp_test.append(explained_variance_score(y[test], final_model.predict(x[test]), multioutput='variance_weighted'))
		print 'MAE : ', mean_squared_error(y[test], final_model.predict(x[test]))
		print 'Explained Variance Score : ', explained_variance_score(y[test], final_model.predict(x[test]))
		print 'r2 score: ' , r2_score(y[test], final_model.predict(x[test]))
		fig, ax = plt.subplots()
		ax.scatter(y[test],final_model.predict(x[test]),y[test])
		ax.plot([y[test].min(), y[test].max()], [y[test].min(), y[test].max()], 'k--', lw=4)
		ax.set_xlabel('Predicted')
		ax.set_ylabel('Measured')
		name = `i`+ '_test.png'
		fig.savefig(name)   # save the figure to file
		plt.close(fig)

	print(np.mean(sPCA_MAE),np.mean(sPCA_r2),np.mean(sPCA_exp))
	print(np.mean(sPCA_MAE_test),np.mean(sPCA_r2_test),np.mean(sPCA_exp_test))

	sys.stdout.close()
	        
sio.savemat('lowrank.mat',{'L': L})
sio.savemat('outliers.mat',{'E': E})