from inspect import _empty
import os
import json
import time
import glob
import discord
import re
import pandas as pd
from dotenv import dotenv_values
from discord import Client, Embed, Webhook, RequestsWebhookAdapter, AsyncWebhookAdapter
from discord.ext import commands

config = dotenv_values(".env")

# env variables
WEBHOOK_URL = config['webhook_url']
OWNER = int(config['owner_id'])
bot_token = config['token']
prefix = config['prefix']

general_warn_message = 'PLEASE CONTACT THE CREATOR. THIS IS PROBABLY A EDGE CASE.'

client = Client()


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # EMOJI TESTER
    if message.content.startswith(prefix + '_emoji'):
        if (message.author.id == OWNER):
            cleaned_message = message.content.split(' ', 1)[1]
            await message.channel.send(find_and_replace_emotes(cleaned_message, False))

    # CHANNEL TESTER
    if message.content.startswith(prefix + '_channel'):
        if (message.author.id == OWNER):
            cleaned_message = message.content.split(' ', 1)[1]
            await message.channel.send(get_channel_id(cleaned_message))

    # SETUP FUNCTION
    if message.content.startswith(prefix + '_setup'):
        if (message.author.id == OWNER):
            categories = []
            subcategories = []
            path_to_json = 'import/'
            json_files = [pos_json for pos_json in os.listdir(
                path_to_json) if pos_json.endswith('.json')]
            for index, js in enumerate(json_files):
                with open(os.path.join(path_to_json, js), encoding="utf8") as json_file:
                    json_text = json.load(json_file)
                    print(json_text)
            await message.channel.send('Setup')

    # IMPORT FUNCTION
    if message.content.startswith(prefix + '_singular'):
        get_params = message.content.split(' ', 1)[1]
        if (message.author.id == OWNER):
            if (get_params == 'all'):
                await message.channel.send('import all')
            else:
                import_singular(message)


def import_all(message):
    return 'import all'

# IMPORT FROM SINGULAR FILE


def import_singular(message):
    get_params = message.content.split(' ', 1)[1]
    raw_file = open('importing/' + get_params + '.json', encoding="utf8")
    imported_messages = json.load(raw_file)
    sum = 0
    for index, import_message in enumerate(imported_messages['messages']):
        time.sleep(0.75)
        webhook = Webhook.from_url(
            WEBHOOK_URL, adapter=RequestsWebhookAdapter())  # Initializing webhook
        message = import_message['content']
        username = import_message['author']['name']
        author_id = import_message['author']['id']
        avatar_image = import_message['author']['avatarUrl']
        past_message_author_id = imported_messages['messages'][index -
                                                               1]['author']['id']
        discriminator = import_message['author']['discriminator']
        message_to_be_sent = ''

        # Helper
        embed_mode = False
        attachment_mode = False

        # Search Helper
        if (author_id != past_message_author_id):
            if (username == 'Deleted User'):
                new_message = 'Search Helper: ' + username + '\n'
                # Executing webhook.
                webhook.send(
                    username=username, avatar_url=avatar_image, content=new_message)
            else:
                new_message = 'Search Helper: ' + username + '#' + \
                    discriminator + ' ' + \
                    import_message['author']['id'] + '\n'
                webhook.send(
                    username=username, avatar_url=avatar_image, content=new_message)

        # determine the message
        if (message != ''):
            message_to_be_sent = message
        # attachments
        elif ('attachments' in import_message and len(import_message['attachments']) > 0):
            if ('url' in import_message['attachments'][0]):
                attachment_mode = True
                message_to_be_sent = import_message['attachments'][0]['url']
            else:
                message_to_be_sent = 'ERROR 405050. MESSAGE_ID:' + \
                    import_message['id'] + '\n' + general_warn_message
        # embeds
        elif ('embeds' in import_message and len(import_message['embeds']) > 0):
            message_embed = import_message['embeds'][0]
            if ('fields' in message_embed and len(message_embed['fields']) > 0):
                embed_mode = True
                message_to_be_sent = Embed(
                    title="", description="")
                for index, embed_message in enumerate(message_embed['fields']):
                    message_to_be_sent.add_field(
                        name=embed_message['name'], value=embed_message['value'], inline=embed_message['isInline'])
            elif ('image' in message_embed and len(message_embed['image']) > 0):
                embed_mode = True
                message_to_be_sent = Embed(
                    title=message_embed['title'], description=message_embed['image']['url'])
            elif ('description' in message_embed and len(message_embed['description']) > 0):
                embed_mode = True
                message_to_be_sent = Embed(
                    title=message_embed['title'], description=message_embed['description'])
            else:
                message_to_be_sent = 'ERROR 405051. MESSAGE_ID:' + \
                    import_message['id'] + '\n' + general_warn_message
        # mentions
        elif ('mentions' in import_message and len(import_message['mentions']) > 0):
            for index, mention_message in enumerate(import_message['mentions']):
                message_to_be_sent += mention_message['nickname'] + ' '

        else:
            message_to_be_sent = 'ERROR 405052. MESSAGE_ID:' + \
                import_message['id'] + '\n' + general_warn_message

        # send the message
        if (embed_mode):
            webhook.send(
                username=username, avatar_url=avatar_image, embed=message_to_be_sent)
            embed_mode = False
        elif (attachment_mode):
            webhook.send(
                username=username, avatar_url=avatar_image, content=message_to_be_sent)
            attachment_mode = False
        else:
            # detect if there are emojis in the string
            webhook.send(username=username, avatar_url=avatar_image,
                         content=find_and_replace_emotes(message_to_be_sent, True))

        sum += 1
        print('Remaining messages: ', len(imported_messages['messages']) - sum)
    raw_file.close()

# FIND EMOTES


def get_emote(emoji):
    for i in client.guilds:
        emoji = discord.utils.get(i.emojis, name=emoji)
    if (emoji != 'None'):
        return emoji
    else:
        return None

# FIND CHANNEL ID BY NAME


def get_channel_id(name):
    channel = discord.utils.get(client.get_all_channels(), name=name)
    return channel.id

# LOCATE AND REPLACE EMOTES
#'<:' + emote_name + ':' + emote_id  + '>'


def find_and_replace_emotes(message_string, debug_mode):
    debug_string = "Error"
    found_emojis = False
    if (len(re.findall(":", message_string)) > 1):
        # 32 max size names
        pattern = r'[^\(]*\:(?P<contents>[^\(]+)\:'
        all_emojis = re.findall(pattern, message_string)
        if all_emojis:
            for emoji in all_emojis:
                len_e = len(emoji)
                if (len_e <= 32 and len_e >= 1):
                    if (get_emote(emoji)):
                        found_emojis = True
                        message_string.replace(
                            ':' + emoji + ':', str(get_emote(emoji)))
        else:
            debug_string = "There's no emojis"

    if (debug_mode == False):
        if (found_emojis):
            debug_string = "Emojis found: " + message_string
            return debug_string
        else:
            return debug_string

    return message_string


client.run(bot_token)
