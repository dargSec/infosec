import json 
import boto3
import logging 
from enum import Enum
from datetime import datetime, timedelta, timezone 
from botocore.exceptions import ClientError

class DateToSendEmail(Enum):
    ALMOST_EXPIRING_KEY = 11
    EXPIRED_KEY = 180


#Initiates aws iam and ses services client
iam_client = boto3.client('iam')
ses_client = boto3.client('ses')


class ActiveUserData:
    user_data = dict()
    access_keys = dict() 
  

def get_iam_users():
    users_list = []
    for iam_user in iam_client.list_users()['Users']:
        users_list.append(iam_user)
    return users_list


def get_iam_active_users(users_list):
    active_user_list = []
    for user in users_list:
        response = iam_client.list_access_keys(UserName=user['UserName'])
        access_keys = response['AccessKeyMetadata']
        for key in access_keys:
            if key['Status'] == 'Active':
                u = ActiveUserData()
                u.user_data = user
                u.access_keys = key
                active_user_list.append(u)
    return active_user_list


#diff between today and the access key creation date
def key_age(keycreatedtime):
    return (datetime.now(timezone.utc) - keycreatedtime).days


def get_email_data(active_user):
    response = iam_client.list_user_tags(UserName=active_user.user_data['UserName'])
    print(response)
    for t in response['Tags']:
        print(t)
        if t['Key'] == 'Owner':
            owner_email = t['Value']
        if t['Key'] == 'Team':
            team_email = t['Value']
    return owner_email,team_email

#compose email for the keys with 30 days to expire
def compose_email(active_user):
    user_email, team_email = get_email_data(active_user)
    user_name = active_user.user_data['UserName']
    access_key = active_user.access_keys['AccessKeyId']
    print(user_name)
    email_body = f"""
    Hi,
    
    The AWS access key {access_key} of the IAM user {user_name} must be rotated within the next 30 days.
    An incident will be open by IAM Team if the rotation is not performed.
    
    Regards,
    IAM Team"""
    print(email_body)
    destination = {'ToAddresses': [user_email], 'CcAddresses': [team_email]}
    message = {
                'Body': {'Text': {'Charset': 'UTF-8', 'Data': email_body}},
                'Subject': {'Charset': 'UTF-8',
                            'Data': f'AWS notification; {user_name} credentials must be renewed'}
             }
    print(destination)
    print(message)
    
    return destination,message


#compose email for the keys already expired, more then 180 days
def compose_email_final(active_user):
    user_email, team_email = get_email_data(active_user)
    user_name = active_user.user_data['UserName']
    access_key = active_user.access_keys['AccessKeyId']
    print(user_name)
    email_body = f"""
    Hi,
    
    The AWS access key {access_key} of the IAM user {user_name} has more than 180 days.
    An incident will be open by IAM Team, please proceed with the rotation asap.
    
    Regards,
    IAM Team"""
    print(email_body)
    destination = {'ToAddresses': [user_email], 'CcAddresses': [team_email]}
    message = {
                'Body': {'Text': {'Charset': 'UTF-8', 'Data': email_body}},
                'Subject': {'Charset': 'UTF-8',
                            'Data': f'AWS notification; {user_name} credentials must be renewed'}
             }
    print(destination)
    print(message)
    
    return destination,message


def lambda_handler(event, context):
    
    users_list = get_iam_users()
    active_users = get_iam_active_users(users_list)
    
    
    print("this file")

    for u in active_users:
        print(u.user_data)
        print(u.access_keys)
    
    for u in active_users:
        print(key_age(u.access_keys['CreateDate']))
        if key_age(u.access_keys['CreateDate']) == DateToSendEmail.ALMOST_EXPIRING_KEY.value:
            #print("pedi")
            #print(key_age(u.access_keys['CreateDate']))
            user_email, team_email = get_email_data(u)
            #print("main")
            #print(user_email)
            #print(team_email)
            destination,message = compose_email(u)
            ses_response = ses_client.send_email(Destination = destination, Message = message, Source = 'example@gmail.com')
        elif key_age(u.access_keys['CreateDate']) == DateToSendEmail.EXPIRED_KEY.value:
            #print("pedi")
            #print(key_age(u.access_keys['CreateDate']))
            user_email, team_email = get_email_data(u)
            #print("main")
            #print(user_email)
            #print(team_email)
            destination,message = compose_email_final(u)
            ses_response = ses_client.send_email(Destination = destination, Message = message, Source = 'example@gmail.com')
