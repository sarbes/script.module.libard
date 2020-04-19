# -*- coding: utf-8 -*-
import json
import requests
import libardgraphqlqueries as q

graphqlUrl = 'https://api.ardmediathek.de/public-gateway'
#graphqlUrl = 'https://api-ifa.ardmediathek.de/public-gateway'
#graphqlUrl = 'https://api-origin-test.ardmediathek.de/public-gateway'
#graphqlUrl = 'https://api-origin-dev.ardmediathek.de/public-gateway'
#graphqlUrl = 'https://api-beta.ardmediathek.de/public-gateway'

#api-test.ardmediathek.de/public-gateway
#api-dev.ardmediathek.de/public-gateway
#api-origin.ardmediathek.de/public-gateway

deviceType = 'pc'
#deviceType = 'tv'
#deviceType = 'responsive'
#deviceType = 'mobile'
#deviceType = 'amazon'

headers = {'content-type':'application/json'}

class parser:
	def __init__(self):
		self.result = {'items':[], 'content':'movies', 'pagination':{'currentPage':0}}

	def setContend(self,content):
		self.result['content'] = content

	def setParams(self,params):
		self.params = params
		
	def setPlugin(self,plugin):
		self.plugin = plugin

	def parseDefaultPage(self,client,name):
		p = json.dumps({'query': q.queryDefaultPage ,'variables':{'client':client, 'name': name}})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()
		for widget in j['data']['defaultPage']['widgets']:
			d = {'type':'dir', 'params':{'mode':'libArdListWidget'}, 'metadata':{}}
			d['metadata']['name'] = widget['title']
			d['params']['widgetId'] = widget['id']
			d['params']['client'] = client
			if widget['type'] != 'stage' and d['metadata']['name'] != 'Livestreams':
				self.result['items'].append(d)
		return self.result

	def parseShows(self,client='ard'):
		p = json.dumps({'query': q.queryShows + q.fragmentTeaser + q.fragmentTeaserImages,'variables':f'{{"client":"{client}"}}'})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()
		for letter in j['data']['showsPage']['glossary']:
			for teaser in j['data']['showsPage']['glossary'][letter]:
				self._grabTeaser(teaser,client)
		return self.result

	def parseShow(self,client='ard',showId=''):
		p = json.dumps({'query': q.queryShow + q.fragmentTeaser + q.fragmentTeaserImages,'variables':f'{{"client":"{client}","showId":"{showId}"}}'})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()
		for teaser in j['data']['showPage']['teasers']:
			self._grabTeaser(teaser,client)
		self.result['fanart'] = j['data']['showPage']['image']['src'].replace('{width}','1920')
		return self.result

	def parseChannels(self):
		p = json.dumps({'query': q.queryChannels,'variables':'{}'})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()
		for channel in j['data']['channels']:
			d = {'type':'dir', 'params':{}, 'metadata':{}}
			d['metadata']['name'] = channel['title'].replace('Stage ','')
			d['params']['channel'] = channel['channelKey']
			self.result['items'].append(d)
		return self.result

	def parseProgram(self,client='daserste',startDate='2019-08-30'):
		p = json.dumps({'query': q.queryProgramPage + q.fragmentTeaser + q.fragmentTeaserImages,'variables':f'{{"client":"{client}","startDate":"{startDate}"}}'})
		#qlRequest = {}
		#qlRequest['query'] = q.queryProgramPage + q.fragmentTeaser + q.fragmentTeaserImages
		#qlRequest['variables'] = {}
		#qlRequest['variables']['client'] = client
		#qlRequest['variables']['startDate'] = startDate
		j = requests.post(graphqlUrl,headers=headers,data=p).json()
		print(json.dumps(j))
		for teaser in j['data']['programPage']['widgets'][0]['teasers']:
			self._grabTeaser(teaser)
		return self.result

	def parseWidget(self,widgetId='4o5DEpNx9uMOSmAceOCass',client='ard'):
		p = json.dumps({'query': q.queryWidgets + q.fragmentTeaser + q.fragmentTeaserImages,'variables':'{"widgetId":"'+widgetId+'","client":"'+client+'"}'})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()
		for teaser in j['data']['widget']['teasers']:
			self._grabTeaser(teaser,client)
		self._grabPagination(j['data']['widget']['pagination'])
		return self.result

	def parseMorePage(self,client,compilationId):
		qlRequest = {}
		qlRequest['query'] = q.queryMorePage + q.fragmentTeaser + q.fragmentTeaserImages
		qlRequest['variables'] = {}
		qlRequest['variables']['client'] = client
		qlRequest['variables']['compilationId'] = compilationId
		j = requests.post(graphqlUrl,headers=headers,data=json.dumps(qlRequest)).json()
		for teaser in j['data']['morePage']['widget']['teasers']:
			self._grabTeaser(teaser)#,client)
		return self.result

	def parseSearchVOD(self,client='ard',text=''):
		p = json.dumps({'query': q.querySearchPageVOD + q.fragmentTeaser + q.fragmentTeaserImages,'variables':f'{{"client":"{client}", "text":"{text}"}}'})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()
		for teaser in j['data']['searchPage']['vodResults']:
			self._grabTeaser(teaser,client)
		return self.result

	def parseVideo(self,clipId='Y3JpZDovL2JyLmRlL3ZpZGVvL2NkNzBjODMwLTM2ZTAtNDljNC1iMDJiLTQyNWNhMWIyZDg3NA',client="ard"):
		p = json.dumps({'query': q.queryVideo ,'variables':{'client':client, 'clipId': clipId, 'deviceType': deviceType}})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()
		for item in j['data']['playerPage']['mediaCollection']['_mediaArray'][0]['_mediaStreamArray']:
			if item['_quality'] == 'auto':
				url = item['_stream'][0]
		if url.startswith('//'): 
			url = 'http:' + url
		d = {'media':[{'url':url, 'stream':'HLS'}]}
		if j['data']['playerPage']['mediaCollection']['_subtitleUrl'] != None:
			d['subtitle'] = [{'url':j['data']['playerPage']['mediaCollection']['_subtitleUrl'], 'type':'ttml', 'lang':'de', 'colour':True}]
		return d


	def _grabTeaser(self,teaser,client=False):
		d = {'params':{}, 'metadata':{'art':{}}}
		d['metadata']['name'] = teaser['shortTitle']
		d['metadata']['plotoutline'] = teaser['longTitle']
		d['metadata']['duration'] = teaser['duration']
		if teaser['images']['aspect16x9']:
			d['metadata']['art']['thumb'] = teaser['images']['aspect16x9']['src'].replace('{width}','512')
		if teaser['images']['aspect3x4']:
			d['metadata']['art']['poster'] = teaser['images']['aspect3x4']['src'].replace('{width}','512')
		if client:
			d['params']['client'] = client
		if teaser['type'] == 'compilation':
			d['params']['compilationId'] = teaser['links']['target']['id']
			d['type'] = 'dir'
			d['params']['mode'] = 'libArdListMorePage'
		elif teaser['type'] == 'show':
			d['params']['showId'] = teaser['links']['target']['id']
			d['type'] = 'dir'
			d['params']['mode'] = 'libArdListShow'
		elif teaser['type'] == 'poster':
			d['type'] = 'movie'
			d['params']['mode'] = 'libArdPlay'
		else:
			d['type'] = 'video'
			d['params']['mode'] = 'libArdPlay'

		if teaser['subtitled']:
			d['metadata']['hassubtitles'] = True

		if 'links' in teaser and 'target' in teaser['links'] and 'id' in teaser['links']['target']:
			d['params']['id'] = teaser['links']['target']['id']
			self.result['items'].append(d)
		return

	def _grabPagination(self,p):
		return
		self.result['pagination']['currentPage'] = p['pageNumber']
		self.result['pagination']['pages'] = []
		lastPage = int((p['totalElements']-1)/20)
		for i in range(0,lastPage+1):
			d = self.params
			d['pageNumber'] = i
			self.result['pagination']['pages'].append(d)
		return


