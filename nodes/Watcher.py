from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import time
import json
import os
# current_directory = os.getcwd()
# print('Watcher:',current_directory)

def save_to_json(file_path, data):
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f)
    except Exception as e:
            print(e)

def read_from_json(file_path):
    data={}
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
            print(e)
    return data


# read_from_json()
current_path = os.path.abspath(os.path.dirname(__file__))
config_json=os.path.join(current_path,'config.json')
# print('Watcher:',config_json)

def read_config():
    config={}
    try:
        if os.path.exists(config_json):
            config=read_from_json(config_json)
    except Exception as e:
            print(e)  
    return config


class FolderWatcher:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        
        if folder_path:
            config=read_config()
            config['folder_path']=folder_path
            save_to_json(config_json,config)

        self.observer = None
        self.event_handler = self._create_event_handler()
        self.status = "Not started"
        self.event_type='-'
        
    def _create_event_handler(self):

        class EventHandler(FileSystemEventHandler):
            def on_any_event(self, event):
                
                if event.is_directory:
                    return
                elif event.event_type == 'created':
                    print(f"File created: {event.src_path}")
                    self.event_type=event.event_type+'_'+str(int(time.time()))
                elif event.event_type == 'deleted':
                    print(f"File deleted: {event.src_path}")
                    self.event_type=event.event_type+'_'+str(int(time.time()))
                elif event.event_type == 'modified':
                    print(f"File modified: {event.src_path}")
                    self.event_type=event.event_type+'_'+str(int(time.time()))
                elif event.event_type == 'moved':
                    print(f"File moved: {event.src_path} to {event.dest_path}")
                    self.event_type=event.event_type+'_'+str(int(time.time()))

                print(event.event_type)
                config=read_config()
                config['event_type']=self.event_type
                save_to_json(config_json,config)

        return EventHandler()

    def set_folder_path(self, new_folder_path):
        self.folder_path = new_folder_path
        if new_folder_path:
            config=read_config()
            config['folder_path']=new_folder_path
            save_to_json(config_json,config)
            self.event_type='-'

    def start(self):
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.folder_path, recursive=True)
        self.observer.start()
        self.status = "Listening"
        self.event_type='-'
        print('Listening')

    def stop(self):
        if self.observer!=None:
            self.observer.stop()
            self.observer.join()
            self.observer=None
            self.status = "Stopped"
            self.event_type='-'
        print('Stopped')
    
  

# # 示例用法
# if __name__ == "__main__":
#     folder_path = "C:\\\\Users\\\\38957\\\\Documents\\\\GitHub\\\\extract-anything\\\\outputs"  # 替换为您要监听的文件夹路径

#     watcher_folder = FolderWatcher(folder_path)
#     watcher_folder.start()
#     watcher_folder.stop()

#     watcher_folder.start()
#     watcher_folder.stop()

#     while True:
#         1

