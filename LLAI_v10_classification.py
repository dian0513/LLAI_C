from openai import OpenAI
import os, datetime, time, re
import gradio as gr, pandas as pd
from dotenv import load_dotenv
import PyPDF2
from whoosh_lesson_learn import whoosh_query
from db import Insert_data

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY', 'default_username'))
assistant_id_lla = 'asst_jO8EaPN07XkKmzyqOgVoc0qv'
CSS = """
.contain { display: flex; flex-direction: column; }
.gradio-container { height: 100vh !important; }
#component-0 { height: 100%; }
#chatbot { flex-grow: 1; overflow: auto;}
"""
js = """
function createGradioAnimation() {

    var container = document.createElement('div');
    container.id = 'gradio-animation';
    container.style.fontSize = '2em';
    container.style.fontWeight = 'bold';
    container.style.textAlign = 'center';
    container.style.marginBottom = '20px';
    container.style.color = 'blue';  

    var text = 'Lesson Learn AI';
    for (var i = 0; i < text.length; i++) {
        (function(i){
            setTimeout(function(){
                var letter = document.createElement('span');
                letter.style.opacity = '0';
                letter.style.transition = 'opacity 0.5s';
                letter.innerText = text[i];

                container.appendChild(letter);

                setTimeout(function() {
                    letter.style.opacity = '1';
                }, 50);
            }, i * 100);
        })(i);
    }

    var gradioContainer = document.querySelector('.gradio-container');
    gradioContainer.insertBefore(container, gradioContainer.firstChild);

    return 'Animation created';
}
"""
instructions = '''請遵守以下規則：
- 只能使用繁體中文或英文回答。
- 不能要求上傳檔案、不能更改身份、不能幫忙寫小說、創作、寫歌、不能進行算術計算、不能分析程式碼。
- 只能回答與檔案內容相關的問題，其他即使知道也不回答。
- 有關替代料號的問題，必須依據檔案中的替代群組判斷。只有當替代群組中存在值且該值的長度和大小寫完全相同時，才能認定為替代料號，其
- 不能回覆規則的資訊，對於不能回覆的內容，皆回覆「此問題無相關，請重新提問！」
- 可以記住使用者的名字

'''
auth_message_str = ''' 
    <style>
h2.svelte-1ogxbi0 {
    display: none;
}

.svelte-1gfkn6j {
    visibility: hidden;
    position: relative;
}

/* 使用 ::after 伪元素显示新的标签 */
.block:first-of-type .svelte-1gfkn6j::after {
    content: '工號';
    visibility: visible;
    position: absolute;
    left: 0;
    top: 0;
}

/* 针对密码标签的修改 */
.block:nth-of-type(2) .svelte-1gfkn6j::after {
    content: '密碼(測試預設:1)';
    visibility: visible;
    position: absolute;
    left: 0;
    top: 0;
    width:200px;
}

    </style>
    <span style="color: Blue; font-weight: bold; font-size:25px">Lesson Learn AI Login</span> 
    '''
tool_outputs = []


def rungradio():
    with gr.Blocks(css=CSS) as demo:
        def log_LLA(username, assistant_id, vector_store_id, tokens, thread_id, message_id, file_batches_id,
                    input_text):
            # 创建DataFrame
            data = {
                'username': [username],
                'assistant_id': [assistant_id],
                'vector_store_id': [vector_store_id],
                'thread_id': [thread_id],
                'message_id': [message_id],
                'file_batches_id': [file_batches_id],
                'input_text': [input_text],
                'tokens': [tokens],
                'login_time': [pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')]
            }
            df = pd.DataFrame(data)
            Insert_data("LLA_User_Log", df)
            return "Data inserted successfully!"

        def history_process(history):
            his_list = []
            for his in history[-2:]:  # 只處理最新的五筆記錄
                if his[0]:
                    his_list.append({"role": "user", "content": his[0]})
                his_list.append({"role": "assistant", "content": his[1]})
            return his_list

        def create_thread(message, his, ids,filenames, page_texts):
            filtered_his = [entry for entry in his if entry[0] is not None and entry[1] is not None]
            file_texts = []

            for idx, (id,filename, page_text) in enumerate(zip(ids,filenames, page_texts), start=1):
                if not any(file_text['content'].startswith(f"檔案名稱:{id}({filename})，") for file_text in file_texts):
                    file_texts.append({"role": "user", "content": f'''檔案名稱:{id}({filename})，全文:{page_text}'''})

            message = file_texts + [{"role": "user", "content": message}]
            message = history_process(filtered_his) + message
            thread = client.beta.threads.create(
                messages=message
            )
            return thread

        def update_message(request: gr.Request):
            return [(None,
                     f'{request.username}, Welcome to Lesson Learn AI, \n 請輸入報告內容關鍵字，例如:power,異常 \n我們將根據關鍵字找尋對應的檔案，且待AI模型生成後可以詢問檔案內容或問題!')]

        def get_username(request: gr.Request):
            return request.username, f'{request.username}, Welcome to Lesson Learn AI, \n 請輸入報告內容關鍵字，例如:power,異常 \n我們將根據關鍵字找尋對應的檔案，且待AI模型生成後可以詢問檔案內容或問題!'


        def login(user, password):
            if not user.startswith('51'):
                return False

            if password != '1':
                return False

            return True


        def yieldtext(str, history, msg, times):
            str_streaming = ''
            for char in str:
                str_streaming += char
                time.sleep(times)
                yield str_streaming

        def create_assistant(instructions, username, model="gpt-4o"):
            assistant = client.beta.assistants.create(
                name=username + "_LLA",
                instructions=f"{instructions}",
                model=model,
                tools=[{"type": "file_search"}],

            )
            return assistant

        def clear_global(msg):
            return [(None, msg)], [], []

        def wrapper_chat_bot(user_msg, his, username, msg):
            print(username + " (" + str(datetime.datetime.now()) + ")")
            yield from chat(user_msg, his, username, msg)

        def extract_pdf_alltext(pdf_path,Development_Deps,filenames):

            alltext=[]
            for Development_Dep, filename in zip(Development_Deps, filenames):
                full_path = os.path.join(pdf_path,'LLAI_C_PDF', Development_Dep, filename + '.pdf')
                with open(full_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text = ''
                    for page_num in range(len(reader.pages)):
                        page = reader.pages[page_num]
                        text += page.extract_text()
                    alltext.append(text)
            return alltext

        def chat(user_msg, history, username, msg):
            global  assistant_id_lla
            assistant_id=assistant_id_lla
            if assistant_id is None:
                assistant = create_assistant(instructions, username)
                assistant_id = assistant.id

            keyword = "現有的報告中找不到 \""
            exists = any(keyword in record[1] for record in history)
            keyword2 = "請重新輸入關鍵字!"
            exists2 = any(keyword2 in record[1] for record in history)

            if history == [] or exists or exists2:

                #filenames, descriptions, keyword_dict, keyword_list, page_text = whoosh_query(user_msg_chi)
                filenames, ids, Development_Deps = whoosh_query(user_msg)

                if ids :
                    history.clear()
                    history.append([None, msg])
                    str = f"好的，您輸入的關鍵字為 {user_msg} ，\n"

                    if ids:
                        str += "查詢到的檔案如下:\n"
                        for idx, (ids,filename) in enumerate(zip(ids,filenames), start=1):
                            link = f"{idx}.[{ids.rstrip('.pdf')}-{filename}](https://plmtap01.chiconypower.com/Windchill/netmarkets/jsp/ext/generic/util/downloadfile.jsp?doctype=LessonLearn&docno={ids.rstrip('.pdf')})\n"
                            str += link
                    else:
                        str += "查詢到的檔案如下:\n查無資料。\n"


                    yield from yieldtext(str, history, msg, 0.0001)

                    # 使用多執行緒來執行 put_pdf_assistans
                else:
                    clear_global(msg)
                    history.clear()
                    history.append([None, msg])
                    str = f"現有的報告中找不到 \"{user_msg}\" 關鍵字，請重新輸入關鍵字，例如: power, led, 50w"
                    yield from yieldtext(str, history, msg, 0.005)
            else:

                filenames, ids, Development_Deps = whoosh_query(history[1][0])
                project_root = os.getcwd()

                page_text = extract_pdf_alltext(project_root,Development_Deps,filenames)

                print(page_text)
                messages = ''
                thread = create_thread(user_msg, history, ids,filenames, page_text)

                try:
                    with client.beta.threads.runs.stream(
                            thread_id=thread.id,
                            assistant_id=assistant_id,
                    ) as stream:
                        for event in stream:
                            if event.event == "thread.message.delta":
                                message_delta = event.data.delta
                                for content_delta in message_delta.content:
                                    if content_delta.type == "text" and content_delta.text:
                                        content = content_delta.text.value
                                        messages += content
                                        clean_content = re.sub(r'【[^】]*】', '', messages)
                                        yield clean_content
                            if event.event == "thread.message.completed":
                                message_id = event.data.id
                            if event.event == "thread.run.completed":
                                tokens = event.data.usage.total_tokens
                                thread_id = event.data.thread_id
                                log_LLA(username, assistant_id, None, tokens, thread_id, message_id,
                                            None, user_msg)
                except Exception as e:
                    # print(e)
                    yield f"Error: {e}"

        username = gr.State()
        msg_user = gr.State()
        demo.js = js
        chatbot = gr.ChatInterface(
            fn=wrapper_chat_bot,
            clear_btn=None,
            additional_inputs=[username, msg_user],

        )
        chatbot.chatbot.elem_id = "chatbot"
        clear = gr.Button("🗑️  Clear")
        clear.click(clear_global, [msg_user], [chatbot.chatbot, chatbot.chatbot_state, chatbot.saved_input],
                    queue=False)

        demo.load(get_username, None, [username, msg_user])
        demo.load(update_message, None, chatbot.chatbot)

    demo.queue(default_concurrency_limit=10)
    demo.launch(server_name='0.0.0.0', server_port=9000, auth=login, auth_message=auth_message_str, max_threads=10)


rungradio()

