import redis
import json

class RedisHandler():
    def __init__(self,host,port,password) :
        self.rds = redis.Redis(host=host,
                               port = port ,
                               password=password,
                            decode_responses=True)
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
    def get_notion_api_key(self,user_id):
        return self.rds.hget(f'user:{user_id}','notion_api_key')
    def get_notion_db_id(self,user_id):
        return self.rds.hget(f'user:{user_id}','notion_db_id')
    def set_notion_db_id(self, user_id, input_text):
        self.rds.hset(f"user:{user_id}", "notion_db_id", input_text)
    def set_notion_api_key(self, user_id, input_text):
        self.rds.hset(f"user:{user_id}", "notion_api_key", input_text)
        
        
    #TODO: 抓取最後一筆對話的文字 拜託
    # def get_last_history(self,user_id):
    #     name = self.get_user_name(user_id)
    #     try:
    #         history = self.rds.lindex(f'message_store:{name}',0)
    #     except Exception as e:
    #         print(e)
    #     data = json.loads(history)
    #     print(data)
    #     return history
        
