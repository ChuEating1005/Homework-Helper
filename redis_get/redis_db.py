import redis
class RedisHandler():
    def __init__(self,host,port,password) :
        self.rds = redis.Redis(host=host,
                               port = port ,
                               password=password,
                            decode_responses=True)
    def get_rds(self):
        return self.rds
    def set_db(self,user_id,user_name,pinecone_index_name):
        self.rds.hmset(f'user:{user_id}',{
            'user_name':user_name,
            "notion_api_key":"",
            "notion_db_id":"",
            "pinecone_index_name":pinecone_index_name,
            "chat_history":""
        })
        
    def get_user_name(self,user_id):
        return self.rds.hget(f'user:{user_id}','user_name')

    def get_user_pinecone_index_name(self,user_id):
        return self.rds.hget(f'user:{user_id}','pinecone_index_name')
    
    def get_chat_history(self,user_id):
        return self.rds.hget(f'user:{user_id}','chat_history')
    
    def set_history(self,user_id,history):
        self.rds.hset(f'user:{user_id}','chat_history',history)