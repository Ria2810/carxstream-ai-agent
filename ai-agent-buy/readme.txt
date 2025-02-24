1.Make sure elasticsearch-layer folder has all dependencies
2.Elastic search zip is the one which make dependencies works


mkdir -p elasticsearch-layer/python
pip install elasticsearch==8.16.0 -t elasticsearch-layer/python
pip install langchain-elasticsearch -t elasticsearch-layer/python

cd elasticsearch-layer && zip -r ../elasticsearch-layer.zip .