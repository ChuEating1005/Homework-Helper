import requests
import notion
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timezone

class Notion:
    def __init__(self, notion_token, databse_id):
        load_dotenv(override=True)
        # you can get your NOTION_TOKEN from notion API integrations
        self.notion_token = notion_token

        # you can get your database key by create a database in notion
        # click share and copy link
        self.database_id = databse_id

        self.headers = {
            "Authorization": "Bearer " + self.notion_token,
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    def get_pages(self, num_pages=None):
        print(f"database id = {self.database_id}")
        url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        
        get_all = num_pages is None
        page_size = 100 if get_all else num_pages
        payload = {"page_size": page_size}
        
        response = requests.post(url, json=payload, headers=self.headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # connect this out to dump aoo data to a file
            with open('db.json', 'w', encoding='utf8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            results = data['results']
            while data["has_more"] and get_all:
                payload = {"page_size": page_size, "start_cursor": data["next_cursor"]}
                url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
                response = requests.post(url, json=payload, headers=self.headers)
                data = response.json()
                results.extend(data["results"])
            return results
        else:
            print("error, status_code != 200")
            return None
            

    def iterate_data(self, pages):
        for page in pages:
            page_id = page["id"]
            props = page["properties"]
            Homework = props["Homework"]["title"][0]["text"]["content"]
            deadline = props["deadline"]["date"]["start"]
            deadline = datetime.fromisoformat(deadline)
            complete = props["complete"]["checkbox"]
            print(Homework, deadline, complete)
            
    def get_page_id_by_name(self, page_name):
        url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        payload = {
            "filter":{
                "property": "Homework",
                "title":{
                    "equals": page_name
                }
            }
        }
        response = requests.post(url, headers=self.headers, json=payload)
        data = response.json()
        if "results" in data and len(data["results"]) > 0:
            page_id = data["results"][0]["id"]
            return page_id
        else:
            print(f"no page found with name: {page_name}")
            return None
    
    def create_page(self, data: dict, text: str):
        create_url = "https://api.notion.com/v1/pages"
        
        payload = {
                    "parent": {"database_id": self.database_id},
                    "properties": data,
                    "children": [
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": text}}]
                            }
                            
                        }
                    ]
                }
        res = requests.post(create_url, headers=self.headers, json=payload)
        print(res.status_code)
        return res

    # if erase_origin: delete the original block and create a new one
    # else add text to original block
    def update_page(self, page_id: str, data: dict, text: str, erase_origin: bool):
        url = f"https://api.notion.com/v1/pages/{page_id}"
        payload = {"properties": data}
        if erase_origin:
            self.delete_block(page_id)
        res = self.new_block(page_id, text)
        print("new block statue:", res)
        res = requests.patch(url, json=payload, headers=self.headers)
        print("update page status:", res.status_code)
        return res
    
    def delete_block(self, page_id):
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        res = requests.get(url, headers=self.headers)
        children = res.json().get("results", [])
        for child in children:
            child_url = f"https://api.notion.com/v1/blocks/{child["id"]}"
            res = requests.delete(child_url, headers=self.headers)
            print("delete child status:", res.status_code)
                
    def new_block(self, page_id, text):
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        payload = {
                    "children": [
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": text}}]
                            }
                        }   
                    ]
                }
        res = requests.patch(url, headers=self.headers, json=payload)
        return res.status_code
    
if __name__ == '__main__':    
    notion = Notion()
    pages = notion.get_pages()
    notion.iterate_data(pages)
    
    # create page
    Homework = 'HW1'
    complete = False
    year = 2025
    month = 5
    day = 20
    hour = 23
    minute = 59
    deadline = datetime(year, month, day, hour, minute).astimezone(timezone.utc).isoformat()
    data = {
        "Homework": {"title": [{"text": {"content": Homework}}]},
        "deadline": {"date": {"start": deadline, "end": None}},
        "complete": {"checkbox": complete}
    }
    text = "erase!"
    # notion.create_page(data, text)
    page_id = notion.get_page_id_by_name("HW2")
    print(f"page_id = {page_id}")
    notion.update_page(page_id, data, text, erase_origin=True)
    
    
        