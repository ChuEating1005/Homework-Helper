import redis

class RedisUser():
    def __init__(self,host,port,password) :
        self.rds = redis.Redis(host=host,
                               port = port ,
                               password=password,
                            decode_responses=True)
    
    def set_user_name(self,user_id,user_name):
        self.rds.hmset(f'user:{user_id}',{
            'user_name':user_name,
            "notion_api_key":"",
            "notion_db_id":"",
            "pinecone_index_name":"",
            "pinecone_environment":"",
            "pinecone_api_key":""
        })
    def get_user_name(self,user_id):
        return self.rds.hget(f'user:{user_id}','user_name')