import requests
import os
import requests
from messages import send_message, send_reply_button, send_list, upload_image
from intents import intent
import re
from requests.auth import HTTPBasicAuth
import json
import datetime

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
    


    def next_question(self, waID, state,custom_msg=""):
        question= intent[state]["question"]+custom_msg
        type=   intent[state]["type"]

        if type == "text":
               self.send_message(waID, question )

        elif type == "list":
            list= intent[state]["list"]
            self.send_list(waID, question, list)

        elif type=="button":
            button= intent[state]["button"]
            self.send_reply_button(waID, question, button)

        else:
            pass


    def restart_chatbot(self, waID):
        self.chat.update_chat(self.number,"lang", "lang", "")
        question= intent["lang"]["question"]
        self.send_list(waID, question, intent["lang"]["list"])

        return True
    
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
    
    


    def processing(self):
        text=self.dict_message['text']
        _type=self.dict_message['type']
        option=""
        item_id=""
        
        custom_msg=""
        order=0
        
        if self.dict_message["type"]=="interactive":
                text =self.dict_message['listReply']["title"]
                option= self.dict_message["listReply"]["title"]
        
        # Checking whether waID present in db or not
        record= self.chat.is_waId_Exists(self.number)

        if record == None:
           print("new")
           self.chat.create_chat(self.number)  
           update=1  
           state="lang"
           new_state=state
        
        else:

            if text=="Restart":
                if self.restart_chatbot(self.number):
                   return "Chat has been Restarted "
                
            
            state=record["state"]
            new_state=state
            update =0

            if state=="lang":
                try:
                    if text.lower() not in ["english", "tamil", "hindi", "telugu", "malayalam", "kannada"]:
                        raise Exception
                    update=1
                    #old_state=state
                    new_state="enroll"
                
                except:
                    err_msg= f"Please Enter a Valid input\n\n{intent[state]['question']}"
                    self.send_list(self.number,err_msg, intent[state]['list'] )

            
            elif state=="enroll":
                #print("inside enroll")
                try:
                    if text.lower() not in ["first time enroll", "enrolled & subscribed", "enrolled not subscribed"]:
                        raise Exception
                    subscription_status= self.chat.get_enroll_status(self.number)

                    if text.lower()=="first time enroll"  :
                        new_state="name"
                        

                    elif text.lower()=="enrolled & subscribed" and subscription_status=="subscribed":
                        new_state="design"

                    
                    elif text.lower()=="enrolled not subscribed" and subscription_status=="enroll":
                        new_state="plan"
                    
                    else:
                        if subscription_status=="subscribed":
                            self.send_message(self.number, "You Have already subscribed")
                            new_state="design"

                        elif subscription_status=="enroll":
                            self.send_message(self.number, "You Have already Enrolled")
                            new_state="plan"
                        else:
                            new_state="name"

                    update=1
                    #old_state=state
                    #print("inside if")
                    
                
                except Exception :
                    #print(e)
                    err_msg= f"Please Enter a Valid input\n\n{intent[state]['question']}"
                    self.send_list(self.number,err_msg, intent[state]['list'] )

            elif state=="name":
                try:
                    if len(text) <3:
                        raise Exception
                    update=1
                    new_state="nickname"
                
                except:
                    err_msg= f"Please Enter a Valid input\n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)

            elif state=="nickname":
                try:
                    if len(text) <3:
                        raise Exception
                    update=1
                    #old_state=state
                    new_state="education"
                
                except:
                    err_msg= f"Please Enter a Valid input\n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)

            elif state=="education":
                try:
                    if len(text) <3:
                        raise Exception
                    update=1
                    #old_state=state
                    new_state="position"
                
                except:
                    err_msg= f"Please Enter a Valid input (Type None for no qualification)\n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)

            
            elif state=="position":
                try:
                    if len(text) <3:
                        raise Exception
                    update=1
                    #old_state=state
                    new_state="face_photo"
                
                except:
                    err_msg= f"Please Enter a Valid input (Type None for no qualification)\n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)

            
            elif state=="face_photo":
                try:
                    if _type!="image" and not allowed_file(text):
                        raise Exception
                    
                    filename= re.findall("data.+", self.dict_message["data"])[0]
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
                    err_msg= f"Please Enter a Valid input (jpg, png, jpeg)\n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)


            elif state=="standing_photo":
                try:
                    if _type!="image" and not allowed_file(text):
                        raise Exception
                    
                    filename= re.findall("data.+", self.dict_message["data"])[0]
                    file_url=upload_image(filename, self.upload)
                    
                    if file_url==False:
                        raise Exception
                    
                    update=1
                    state=f"images.{state}"
                    text=file_url
                    new_state="side_photo"
                
                except:
                    err_msg= f"Please Enter a Valid input (jpg, png, jpeg)\n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)


            elif state=="side_photo":
                try:
                    if _type!="image" and not allowed_file(text):
                        raise Exception
                    
                    filename= re.findall("data.+", self.dict_message["data"])[0]
                    file_url=upload_image(filename, self.upload)
                    
                    if file_url==False:
                        raise Exception
                    
                    update=1
                    #old_state=state
                    state=f"images.{state}"
                    text=file_url
                    new_state="political_party"
                
                except:
                    err_msg= f"Please Enter a Valid input (jpg, png, jpeg)\n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)


            elif state=="political_party":
                try:
                    if text not in ["DMK","ADMK","PMK","BJP","Congress","ntk","Communist","AMMK","DMDK"]:
                        raise Exception
                    update=1
                    #old_state=state
                    new_state="plan"
                
                except:
                    err_msg= f"Please Enter a Valid input \n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)

            
            elif state=="plan":
                try:
                    if option not in ["1500", "2500", "100"]:
                        raise Exception
                    
                    #tot_amount=100 #Testing purpose

                    tot_amount=option
                    payment_data=self.generate_payment_link(tot_amount)
        
                    payment_id=payment_data['id']
                    payment_link=payment_data['short_url']
                     
                    # Creating a payment document in payment collection
                    self.payment.create_payment(payment_id, payment_link)
                    
                    update=1
                    custom_msg=f" of Rs{tot_amount}\n\n{payment_link}"
                    item_id=payment_id
                    new_state="payment"
                
                except Exception as e:
                    print(e)
                    err_msg= f"Please Enter a Valid input \n\n{intent[state]['question']}"
                    self.send_list(self.number,err_msg, intent[state]['list'] )

            elif state=="active_plan":
                pass

            elif state=="payment":

                
                pay_id = self.chat.get_payment_check(self.number)
                payment_status=self.check_payment_status(pay_id)["status"]
                payment_details= self.check_payment_status(pay_id)

                if(payment_status=="paid"):    
                   self.payment.update_payment(pay_id, "paid", payment_details)

                   self.send_message(self.number, "Images")
                   self.send_message(self.number, "Terms and Conditions")

                   update=1
                   
                   state="subscription"
                   text="subscribed"
                   new_state="end"

                else:
                   err_msg="You haven't made the payment .\nPlease pay the amount in the above link to proceed"
                   self.send_message(self.number,err_msg) 
                
            ##------------------------  Enrolled and Subscribed ------------------------------------------------------------ ##
            elif state=="design":
                try:
                 if text.lower() not in ["social media post","banner"]:
                    raise Exception
                 
                   
                 if text.lower()=="social media post":
                     new_state="post_size"
                 else:
                     new_state="banner_size"
                 update=1
                   
                 state="design.design"
                 
                  
                except:
                   err_msg= f"Please Enter a Valid input \n\n{intent[state]['question']}"
                   self.send_list(self.number,err_msg, intent[state]['list'] ) 

            elif state=="banner_size":
                try:  
                    if text not in ["3*3","4*6","8*10","10*8", "12*8"]:
                      raise Exception  
                    update=1
                   
                    state="design.size"
                    order=1
                    new_state="end"
                    
                except:
                    err_msg= f"Please Enter a Valid input \n\n{intent[state]['question']}"
                    self.send_list(self.number,err_msg, intent[state]['list'] )
                    
                    

            elif state=="post_size":
                try:  
                    if text.lower() not in ["whatsapp","facebook","instagram"]:
                      raise Exception  
                    update=1
                   
                    state="design.size"
                    new_state="post_type"
                    
                except:
                    err_msg= f"Please Enter a Valid input \n\n{intent[state]['question']}"
                    self.send_list(self.number,err_msg, intent[state]['list'] )
                    
                    

            elif state=="post_type":
                try:  
                    if text.lower() not in ["image", "video"]:
                      raise Exception  
                    
                    update=1
                   
                    state="design._type"
                    new_state="post_design"

                except:
                    err_msg= f"Please Enter a Valid input \n\n{intent[state]['question']}"
                    self.send_reply_button(self.number,err_msg, intent[state]['button'] )
                    
                    
            
            elif state=="post_design":
                try:  
                    if text not in ["Birthday Post", "Regular Wishes Post","Congratulation Post","Welcome Post", "Achievement Post","Protest Post", "Self Quote Post","Quotes Post","Work Update Post"]:
                      raise Exception  
                    
                    if text in ["Birthday Post", "Congratulation Post","Welcome Post" ]:
                        new_state="post_name"

                    elif text =="Regular Wishes Post":
                        new_state="wish"

                    elif text =="Self Quote Post":
                        new_state="self_quote"

                    elif text =="Quote Post":
                        new_state="quote"

                    elif text == "Work Update Post":
                        new_state="work"

                    update=1
                    state="design.post_design"
                        
                except:
                    err_msg= f"Please Enter a Valid input \n\n{intent[state]['question']}"
                    self.send_list(self.number,err_msg, intent[state]['list'] )
                    
                    

            elif state=="post_name":
                try:
                   if len(text)<3:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   new_state="post_nickname"

                except:
                    err_msg= f"Please Enter a Valid input\n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)

                    

            elif state=="post_nickname":
                try:
                   if len(text)<3:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   new_state="post_photo"
                except:
                    err_msg= f"Please Enter a Valid input\n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)
                    

            elif state=="post_photo":
                try:
                    if _type!="image" and not allowed_file(text):
                        raise Exception
                    
                    filename= re.findall("data.+", self.dict_message["data"])[0]
                    file_url=upload_image(filename, self.upload)
                    
                    if file_url==False:
                        raise Exception
                    
                    update=1
                    #old_state=state
                    state=f"design.{state}"
                    text=file_url
                    new_state="post_age"
                
                except Exception as e:
                    print(e)
                    err_msg= f"Please Enter a Valid input (jpg, png, jpeg)\n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)

            elif state=="post_age":
                try:
                   if text.isnumeric()==False:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   new_state="post_position"
                except:
                    err_msg= f"Please Enter a Valid input\n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)

            elif state=="post_position":
                try:
                   if len(text)<3:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   new_state="post_message"
                except:
                    err_msg= f"Please Enter a Valid input\n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)

            elif state=="post_message":
                try:
                   if len(text)<3:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   new_state="post_photos"
                except:
                    err_msg= f"Please Enter a Valid input\n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)


            elif state=="post_photos":
                try:
                    if _type!="image" and not allowed_file(text):
                        raise Exception
                    
                    filename= re.findall("data.+", self.dict_message["data"])[0]
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
                    print(e)
                    err_msg= f"Please Enter a Valid input (jpg, png, jpeg)\n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)

            # -------------------- Wish Post ----------------------------------------------#
            elif state=="wish":
                try:
                   if text.lower not in ["good morning","good evening","good night", "function wise"]:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   order=1
                   new_state="end"

                except:
                    err_msg= f"Please Enter a Valid input\n\n{intent[state]['question']}"
                    self.send_list(self.number,err_msg, intent[state]['list'] )

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
                    err_msg= f"Please Enter a Valid input\n\n{intent[state]['question']}"
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
                    err_msg= f"Please Enter a Valid input\n\n{intent[state]['question']}"
                    self.send_message(self.number,err_msg)

            # ----------------------------------------------------------------------------- #

            # -------------------------------- Work Update Post ------------------------------ #
            elif state=="work":
                try:
                   if text.lower() not in ["daily","weekly","monthly"]:
                       raise Exception
                   update=1
                   state=f"design.{state}"
                   order=1
                   new_state="end"

                except:
                    err_msg= f"Please Enter a Valid input\n\n{intent[state]['question']}"
                    self.send_reply_button(self.number,err_msg, intent[state]['button'] )

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
                      
                      self.send_message(self.number, "Order Created Successfully")
                   else:
                      self.chat.update_chat(self.number,state, new_state, text)


                elif new_state=="payment" :
                   self.chat.update_chat(self.number,state, new_state, text, item_id)
                   self.next_question(self.number, new_state,custom_msg)
                else:
                    self.chat.update_chat(self.number,state, new_state, text)
                    self.next_question(self.number, new_state,custom_msg)
                


        return "Message Sent"

                    





            
                    


        
        
    
    


               

    


