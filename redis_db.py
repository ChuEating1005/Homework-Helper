import redis

class RedisUser():
    def __init__(self,host,port,password) :
        self.rds = redis.Redis(host=host,port = port ,password=password)
    
    def set_user_name(self,user_id,user_name):
        self.rds.hmset(f'user:{user_id}',{
            'user_name':user_name,
            "notion_api_key":None,
            "notion_db_id":None,
            "pinecone_index_name":None,
            "pinecone_environment":None,
            "pinecone_api_key":None
        })
    def get_user_name(self,user_id):
        return self.rds.hget(f'user:{user_id}','user_name')