import requests
import os
import requests
from messages import send_message, send_reply_button, send_list, upload_image
from intents import intent
import re
from requests.auth import HTTPBasicAuth
import json
import datetime
from googletrans import Translator
from utils import *

allowed_extensions=["png", "jpg", "jpeg"]




def allowed_file(filename):
  ext=filename.split(".")[-1]
  if ext in allowed_extensions:
      return True

class Order():
    def __init__(self, db):
        self.db= db.order

    def check_payment_status(self):
        pass
    
    def create_order(self,post):
        order= post
        order["status"]=""
        order["created_date"]=datetime.datetime.now()
        order["last_modified"]=datetime.datetime.now()
        order=self.db.insert_one(order)
        return order.inserted_id
        


class Payment():
    def __init__(self, db):
        self.db= db.payment
    
    def create_payment(self, payid, url):
        record= {'_id':payid, 
                   "url":url,
                   "status":"not paid"
                   }
        self.db.insert_one(record)

    def update_payment(self, id, status,payment_details):
        payment_details["status"]=status
        payment_details["_id"]=payment_details["id"]
        record={"$set":payment_details}
        self.db.update_one({'_id':id},record)
        


class Chat():
    def __init__(self, db):
        self.db= db.chat

    def is_waId_Exists(self, number):
        return self.db.find_one({"_id":number})
    
    def create_chat(self, number):
        new_user= {'_id':number, 
                   "state":"lang", 
                   "language":"",
                   "name":"",
                   "nickname":"",
                   "education":"",
                   "position":"",
                   "images":{
                       "face_photo":"",
                        "standing_photo":"",
                        "side_photo":""},

                    "plan":"",
                    "political_party":"",
                    "subscription":""
                
                    
                   }
        self.db.insert_one(new_user)

    def update_chat(self, number, key, state, value,id="",order=0):
            old_user={"$set":{"state":state, key :value}}
            if state=="payment":
               old_user["$push"]= { "payment": { "$each": [id] } } 
            
            if order==1:
               
               #Empty design details as order is created
               old_user["$set"]={"state":state,"design":{}}
               #print(old_user)
               old_user["$push"]= { "order": { "$each": [id] } } 

            elif state=="plan":
               old_user["$set"]["subscription"]= "enrolled"
            
            #print(old_user)
            self.db.update_one({'_id':number},old_user)

    def get_post(self, number, key=""):
        data=self.db.find_one({"_id":number})
        return data["design"]

    def get_payment_check(self, number):
        data=self.db.find_one({'_id':number})
        return data["payment"][-1]
    
    def get_enroll_status(self, number):
        data=self.db.find_one({'_id':number})
        return data["subscription"]
    
    def get_chat_lang(self, number):
        data=self.db.find_one({'_id':number})
        return data["lang"]
            

class Bot():
    def __init__(self, db, json, number,  API_URL, ACCESS_TOKEN, upload, pay_user, pay_pass):
        
        self.db=db
        self.chat= Chat(self.db)
        self.order= Order(self.db)
        self.payment= Payment(self.db)

        self.dict_message= json
        self.number = number
        self.APIUrl = API_URL
        self.token = ACCESS_TOKEN

        self.upload=upload

        self.pay_user=pay_user
        self.pay_pass=pay_pass

    

    def send_message(self, waID, text):
        answer = send_message(waID, text)
        return answer
    

    def send_reply_button(self, waID, text, buttons):
        answer = send_reply_button(waID, text, buttons)
        print(answer)
        return answer

    def send_list(self, waID, text, list):
        answer = send_list(waID, text, list)
        return answer
    


    def next_question(self, waID, state,chat_lang, custom_msg=""):
        question= intent[chat_lang][state]["question"]+custom_msg
        type=   intent[chat_lang][state]["type"]

        if type == "text":
               self.send_message(waID, question )

        elif type == "list":
            list= intent[chat_lang][state]["list"]
            self.send_list(waID, question, list)

        elif type=="button":
            button= intent[chat_lang][state]["button"]
            self.send_reply_button(waID, question, button)

        else:
            pass

    
    def restart_chatbot(self, waID):
        self.chat.update_chat(self.number,"lang", "lang", "")
        question= intent["lang"]["question"]
        self.send_list(waID, question, intent["lang"]["list"])

        return True
    
    def keyword_state_change(self,text, state, update, new_state):
        subscription_status= self.chat.get_enroll_status(self.number)
        if subscription_status=="subscribed":
            status=keyword_node(text)
            if status!="None":
                new_state=status
                state="design.post_design"
                update=1
                return state, update, new_state
        return False


    def generate_payment_link(self, amount):
        
        #reference_id = reference_id
        data = {
            "amount": amount,
            "currency": "INR",
            "description": "Testing",
            "options": {
                  "checkout": {
                  "name": "ABC Test Corp"
                              }
  }    
            
            
        }
        data = json.dumps(data)
        headers = {
            'Content-type': 'application/json'
        }
        res = requests.post(url="https://api.razorpay.com/v1/payment_links/", headers=headers, data=data,
                            auth=HTTPBasicAuth(self.pay_user,self.pay_pass)).json()
        #print(res)
        return res
    
    def check_payment_status(self, id):
        
        url=f"https://api.razorpay.com/v1/payment_links/{id}"
    
        headers = {
            'Content-type': 'application/json'
        }
        res = requests.get(url= url, headers=headers,
                            auth=HTTPBasicAuth(self.pay_user, self.pay_pass)).json()
        #print(res)
        return res
    
    def text_translate(self,lang, text):
        translator = Translator()
        result = translator.translate(text, dest=lang)
        return result.text



    def processing(self):
        text=self.dict_message['text']
        _type=self.dict_message['type']
        option=""
        item_id=""
        
        custom_msg=""
        order=0
        chat_lang="english"
        
        
        if self.dict_message["type"]=="interactive":
                text =self.dict_message['listReply']["title"]
                option= self.dict_message["listReply"]["title"]
        
        elif self.dict_message["type"]=="button":
            pass
        
        # Checking whether waID present in db or not
        record= self.chat.is_waId_Exists(self.number)

        
        if record == None:
           print("new")
           self.chat.create_chat(self.number)  
           update=1  
           state="lang"
           new_state=state
           
        
        else:
            chat_lang= self.chat.get_chat_lang(self.number)  # chat lang chosen by user in "lang" step
            state=record["state"]
            new_state=state
            update =0

            if text=="Restart":
                if self.restart_chatbot(self.number):
                   return "Chat has been Restarted "
                
            node_change_list= self.keyword_state_change(text,state,update,new_state)
            if node_change_list !=False:
                state=node_change_list[0]
                update=node_change_list[1]
                new_state=node_change_list[2]

            
            if state=="lang":
                try:
                    text=text.lower()
                    if text not in ["english", "tamil", "hindi", "telugu", "malayalam", "kannada"]:
                        raise Exception
                    update=1
                    #old_state=state
                    chat_lang=text
                    new_state="enroll"
                
                except Exception as e:
                    print(e)
                    err_msg= f"Please Enter a Valid input\n\n{intent[state]['question']}"
                    self.send_list(self.number,err_msg, intent[state]['list'] )

            
            elif state=="enroll":
                #print("inside enroll")
                try:
                    if text.lower() not in enroll_list[chat_lang]:
                        raise Exception
                    subscription_status= self.chat.get_enroll_status(self.number)

                    if text.lower() in ["first time enroll","முதல் பதிவு"]  :
                        new_state="name"
                        

                    elif text.lower() in ["enrolled & subscribed","சந்தா"] and subscription_status=="subscribed":
                        new_state="design"

                    
                    elif text.lower() in ["enrolled not subscribed","குழுசேரவில்லை"] and subscription_status=="enroll":
                        new_state="plan"
                    
                    else:
                        if subscription_status=="subscribed":
                            msg= self.text_translate(chat_lang,"You Have already subscribed")
                            self.send_message(self.number,msg )
                            new_state="design"

                        elif subscription_status=="enroll":
                            msg= self.text_translate(chat_lang,"You Have already subscribed")
                            self.send_message(self.number, msg)
                            new_state="plan"
                        else:
                            new_state="name"

                    update=1
                    #old_state=state
                    #print("inside if")
                    
                
                except Exception :
                    #print(e)
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_list(self.number,err_msg, intent[chat_lang][state]['list'] )

            elif state=="name":
                try:
                    if len(text) <3:
                        raise Exception
                    update=1
                    new_state="nickname"
                
                except:
                    
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)

            elif state=="nickname":
                try:
                    if len(text) <3:
                        raise Exception
                    update=1
                    #old_state=state
                    new_state="education"
                
                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)

            elif state=="education":
                try:
                    if len(text) <3:
                        raise Exception
                    update=1
                    #old_state=state
                    new_state="position"
                
                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input (Type None for no qualification)")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)

            
            elif state=="position":
                try:
                    if len(text) <3:
                        raise Exception
                    update=1
                    #old_state=state
                    new_state="face_photo"
                
                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)

            
            elif state=="face_photo":
                try:
                    filename= re.findall("data.+", self.dict_message["data"])[0]
                    if (_type!="image" or _type!="document") and not allowed_file(filename):
                        
                        raise Exception
                    
                    
                    file_url=upload_image(filename, self.upload)
                    
                    if file_url==False:
                        raise Exception
                    
                    update=1
                    #old_state=state
                    state=f"images.{state}"
                    text=file_url
                    new_state="standing_photo"
                
                except Exception as e: 
                    print(e)
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input (jpg, png, jpeg)")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)


            elif state=="standing_photo":
                try:
                    filename= re.findall("data.+", self.dict_message["data"])[0]
                    if (_type!="image" or _type!="document") and not allowed_file(filename):
                        raise Exception
                    
                    
                    file_url=upload_image(filename, self.upload)
                    
                    if file_url==False:
                        raise Exception
                    
                    update=1
                    state=f"images.{state}"
                    text=file_url
                    new_state="side_photo"
                
                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input (jpg, png, jpeg)")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)


            elif state=="side_photo":
                try:
                    filename= re.findall("data.+", self.dict_message["data"])[0]
                    if (_type!="image" or _type!="document") and not allowed_file(filename):
                        raise Exception
                    
                    
                    file_url=upload_image(filename, self.upload)
                    
                    if file_url==False:
                        raise Exception
                    
                    update=1
                    #old_state=state
                    state=f"images.{state}"
                    text=file_url
                    new_state="political_party"
                
                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input (jpg, png, jpeg)")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)


            elif state=="political_party":
                try:
                    if text not in political_party_list[chat_lang]:
                        raise Exception
                    update=1
                    #old_state=state
                    new_state="plan"
                
                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_list(self.number,err_msg, intent[chat_lang][state]['list'] )

            
            elif state=="plan":
                try:
                    if text not in ["Rs 1500", "Rs 2500", "Rs 100"]:
                        raise Exception
                    
                    #tot_amount=100 #Testing purpose
                    text= re.findall("\d+", text)[0]
                    tot_amount=int(text)
                    payment_data=self.generate_payment_link(tot_amount*100)
                    payment_id=payment_data['id']
                    payment_link=payment_data['short_url']
                     
                    # Creating a payment document in payment collection
                    self.payment.create_payment(payment_id, payment_link)
                    
                    update=1

                    
                    custom_msg=f"{tot_amount}\n\n{payment_link}"
                    item_id=payment_id
                    new_state="payment"
                
                except Exception :
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_list(self.number,err_msg, intent[chat_lang][state]['list'] )

            

            elif state=="payment":

                
                pay_id = self.chat.get_payment_check(self.number)
                payment_status=self.check_payment_status(pay_id)["status"]
                payment_details= self.check_payment_status(pay_id)

                if(payment_status=="paid"):    
                   self.payment.update_payment(pay_id, "paid", payment_details)
                   
                   msg1 = self.text_translate(chat_lang,"Images")
                   msg2 = self.text_translate(chat_lang,"Terms and Conditions")
                   self.send_message(self.number, msg1)
                   self.send_message(self.number, msg2)

                   update=1
                   
                   state="subscription"
                   text="subscribed"
                   new_state="end"

                else:
                   warning_msg= self.text_translate(chat_lang, "You haven't made the payment .\nPlease pay the amount in the above link to proceed")
                   err_msg= f"{warning_msg}"
                   self.send_message(self.number,err_msg) 
                
            ##------------------------  Enrolled and Subscribed ------------------------------------------------------------ ##
            elif state=="design":
                try:
                 if text.lower() not in design_list[chat_lang]:
                    raise Exception
                 
                   
                 if text.lower()=="social media post" or text=="சமூக ஊடக இடுகை":
                     new_state="post_size"
                 else:
                     new_state="banner_size"
                 update=1
                   
                 state="design.design"
                 
                  
                except:
                   warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                   err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                   self.send_list(self.number,err_msg, intent[chat_lang][state]['list'] ) 

            elif state=="banner_size":
                try:  
                    if text not in ["3*3","4*6","8*10","10*8", "12*8"]:
                      raise Exception  
                    update=1
                   
                    state="design.size"
                    order=1
                    new_state="end"
                    
                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_list(self.number,err_msg, intent[chat_lang][state]['list'] )
                    
                    

            elif state=="post_size":
                try:  
                    if text.lower() not in post_size_list[chat_lang]:
                      raise Exception  
                    update=1
                   
                    state="design.size"
                    new_state="post_type"
                    
                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_list(self.number,err_msg, intent[chat_lang][state]['list'] )
                    
                    

            elif state=="post_type":
                try:  
                    if text.lower() not in post_type_list[chat_lang]:
                      raise Exception  
                    
                    update=1
                   
                    state="design._type"
                    new_state="post_design"

                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_reply_button(self.number,err_msg, intent[chat_lang][state]['button'] )
                    
                    
            
            elif state=="post_design":
                try:  
                    if text.lower() not in post_design_list[chat_lang]:
                      raise Exception  
                    
                    if text in ["Birthday Post", "Congratulation Post","Welcome Post","பிறந்தநாள் இடுகை", "வாழ்த்து இடுகை", "வரவேற்பு இடுகை" ]:
                        new_state="post_name"

                    elif text in ["Regular Wishes Post","வழக்கமான வாழ்த்து பதிவு"]:
                        new_state="wish"

                    elif text in ["Self Quote Post", "சுய மேற்கோள் இடுகை"]:
                        new_state="self_quote"

                    elif text in ["Quotes Post","மேற்கோள் இடுகை"]:
                        new_state="quote"

                    elif text in ["Work Update Post", "பணி புதுப்பிப்பு இடுகை"]:
                        new_state="work"

                    update=1
                    state="design.post_design"
                        
                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_list(self.number,err_msg, intent[chat_lang][state]['list'] )
                    
                    

            elif state=="post_name":
                try:
                   if len(text)<3:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   new_state="post_nickname"

                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)

                    

            elif state=="post_nickname":
                try:
                   if len(text)<3:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   new_state="post_photo"
                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)
                    

            elif state=="post_photo":
                try:
                    filename= re.findall("data.+", self.dict_message["data"])[0]
                    if (_type!="image" or _type!="document") and not allowed_file(filename):
                        raise Exception
                    
                    
                    file_url=upload_image(filename, self.upload)
                    
                    if file_url==False:
                        raise Exception
                    
                    update=1
                    #old_state=state
                    state=f"design.{state}"
                    text=file_url
                    new_state="post_age"
                
                except Exception as e:
                    #print(e)
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input (jpg, png, jpeg)")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)

            elif state=="post_age":
                try:
                   if text.isnumeric()==False:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   new_state="post_position"
                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)

            elif state=="post_position":
                try:
                   if len(text)<3:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   new_state="post_message"
                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)

            elif state=="post_message":
                try:
                   if len(text)<3:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   new_state="post_photos"
                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)


            elif state=="post_photos":
                try:
                    filename= re.findall("data.+", self.dict_message["data"])[0]
                    if (_type!="image" or _type!="document") and not allowed_file(filename):
                        raise Exception
                    
                    
                    file_url=upload_image(filename, self.upload)
                    
                    if file_url==False:
                        raise Exception
                    
                    update=1
                    #old_state=state
                    state=f"design.{state}"
                    text=file_url
                    order=1
                    new_state="end"
                
                except Exception as e:
                    #print(e)
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input (jpg, png, jpeg)")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)

            # -------------------- Wish Post ----------------------------------------------#
            elif state=="wish":
                try:
                   if text.lower not in wish_list[chat_lang]:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   order=1
                   new_state="end"

                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_list(self.number,err_msg, intent[chat_lang][state]['list'] )

            # ---------------------------------------------------------------------------- #    

            # ------------------------- self Quote Post --------------------------------  #
            elif state=="self_quote":
                try:
                   if len(text)<3:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   order=1
                   new_state="end"

                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)


            # ----------------------------------------------------------------------------# 


            # ----- ----------------------- Quote Post ----------------------------------- #
            elif state=="quote":
                try:
                   if len(text)<-3:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   order=1
                   new_state="end"

                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_message(self.number,err_msg)

            # ----------------------------------------------------------------------------- #

            # -------------------------------- Work Update Post ------------------------------ #
            elif state=="work":
                try:
                   if text.lower() not in work_list[chat_lang]:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   order=1
                   new_state="end"

                except:
                    warning_msg= self.text_translate(chat_lang, "Please Enter a Valid input")
                    err_msg= f"{warning_msg}\n\n{intent[chat_lang][state]['question']}"
                    self.send_reply_button(self.number,err_msg, intent[chat_lang][state]['button'] )

            # -------------------------------------------------------------------------------- #

            ## --------------------------------------------------------------------------------------------------------------------------------- ##
            elif state=="end":
                self.restart_chatbot(self.number)
            

        ##  Updating Coverstion status, details and sending the next question

        if update==1:
                if new_state=="end":
                   if order==1:
                      # Update last details of post before creation of order
                      self.chat.update_chat(self.number,state, new_state, text)

                      # Get details of the post
                      post= self.chat.get_post(self.number)  

                      # Generate order id and create order
                      order_id =self.order.create_order(post)
                      print("Order Created")

                      self.chat.update_chat(self.number,state, new_state, text, order_id, order)
                      
                      success_msg= self.text_translate(chat_lang, "Order Created Successfully")
                      self.send_message(self.number, success_msg )
                   else:
                      self.chat.update_chat(self.number,state, new_state, text)


                elif new_state=="payment" :
                   self.chat.update_chat(self.number,state, new_state, text, item_id)
                   self.next_question(self.number, new_state,chat_lang, custom_msg)
                else:
                    
                    self.chat.update_chat(self.number,state, new_state, text)
                    self.next_question(self.number, new_state,chat_lang, custom_msg)
                


        return "Message Sent"

                    





            
                    


        
        
    
    


               

    


