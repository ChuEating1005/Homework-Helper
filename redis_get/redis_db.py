import redis
import json
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
    
    def get_last_history(self,user_id):
        name = self.get_user_name(user_id)
        history = self.rds.lindex(f'message_store:{name}',0)
        data = json.loads(history)
        print(data)
        return history
        
