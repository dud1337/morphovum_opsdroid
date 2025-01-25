######################################################################
#   
#   MorphOvum Opsdroid
#   Interacting with MorphOvum api via Opsdroid
#   
######################################################################
from opsdroid.skill import Skill
from opsdroid.matchers import match_regex, match_crontab, match_event, match_always
from opsdroid.events import Message, Reaction, Image
from random import choice, randint
from asyncio import sleep

import datetime
import json
import requests
import sched
from hashlib import sha256

class MorphOvumSkill(Skill):
    def __init__(self, *args, **kwargs):
        super(MorphOvumSkill, self).__init__(*args, **kwargs)
        self.session = requests.Session()
        self.api_methods = None
        self.auth()

        self.bot_was_last_message = False


    ##################################################################
    #
    #   1. Avoid spamming
    #       The bot notifies if a stream is ongoing every hour
    #       if no one posts within that hour, it is superfluous;
    #       this functionality prevents that.
    #
    ##################################################################
    async def avoid_spam_send(self, msg):
        if not self.bot_was_last_message:
            await self.opsdroid.send(
                Message(
                    text=msg,
                    target=self.config.get('room_music')
                )
            )
            self.bot_was_last_message = True
        else:
            pass


    @match_always
    async def who_last_said(self, event):
        if hasattr(event, 'target') and event.target == self.config.get('room_music'):
            self.bot_was_last_message = False


    ##################################################################
    #
    #   2. MorphOvum
    #       MorphOvum interaction functionality
    #
    ##################################################################
    def auth(self):
        self.session.post(
            self.config.get('morphovum_api_link') + 'admin',
            data={
                'password_hash':sha256(self.config.get('morphovum_admin_cred').encode('utf-8')).hexdigest()
            }
        )
        try:
            response = self.session.get(
                self.config.get('morphovum_api_link') + 'admin'
            )
            authed = json.loads(response.text)['data']
        except:
            authed = False
        if authed and not self.api_methods:
            self.api_methods = json.loads(self.session.get(self.config.get('morphovum_api_link') + '/help').text)['data']
        return authed

    def append_webpage(self, text):
        return '🎵 ' + self.config.get('morphovum_webpage_link') + ' 🎵 ' + text + ' 🎵'

    async def api_request(self, api_call, arg=None): 
        '''api request'''
        if api_call in self.api_methods:
            url = self.config.get('morphovum_api_link') + api_call.replace('_', '/')
            if self.api_methods[api_call]['arg']:
                output = json.loads(self.session.post(
                    url,
                    data={
                        self.api_methods[api_call]['arg']:arg,
                    }
                ).text)
            else:
                output = json.loads(self.session.get(
                    url
                ).text)

            if output['err']:
                if output['msg'] == 'requires admin privileges':
                    self.auth()
                    await self.api_request(api_call, arg)
                    return
                output = 'Error: ' + output['msg']

            else:
                output = output['msg']
            return output

    
    @match_regex('^!mo reauth$')
    async def re_auth(self, message):
        self.auth()

    @match_crontab('0 0 1 * *', timezone="Europe/Zurich")
    #@match_crontab('* * * * *', timezone="Europe/Zurich")
    async def say_song_interval(self, event):
        await sleep(60 * randint(1, 60 * 24 * 30))
        song_data = json.loads(self.session.get(self.config.get('morphovum_api_link') + 'music/currenttrack').text)

        if song_data['err']:
            msg = 'Error: ' + song_data['msg']
        else:
            msg =  self.append_webpage(song_data['msg'])

        await self.avoid_spam_send(msg)

    @match_regex('^!s$')
    async def say_song(self, message):
        song_data = json.loads(self.session.get(self.config.get('morphovum_api_link') + 'music/currenttrack').text)
        if song_data['err']:
            msg = 'Error: ' + str(song_data['msg'])
        elif song_data['data']['is_playing']:
            msg = self.append_webpage(song_data['msg'])
        else:
            msg = 'Music player is paused'
        
        await message.respond(
            Message(
                text=msg
            )
        )

    @match_regex('^!mo (?P<player>(a|ambience)|(m|music)|(c|clips)|(playlist))[ _]{1}(?P<command>[\w_]+) ?(?P<arg>.+)?$')
    async def called_api_request(self, message):
        api_call = ''

        player = message.entities['player']['value']
        if player in {'m', 'music'}:
            api_call += 'music_'
        elif player in {'a', 'ambience'}:
            api_call += 'ambience_'
        elif player in {'c', 'clips'}:
            api_call += 'clips_'
        elif player in 'playlist':
            api_call +='playlist_'

        api_call += message.entities['command']['value']

        if api_call in self.api_methods:
            if self.api_methods[api_call]['arg']:
                output = await self.api_request(api_call, arg=message.entities['arg']['value'])
            else:
                output = await self.api_request(api_call)
            
            if output:
                await message.respond(
                    Message(
                        text=self.append_webpage(output)
                    )
                )

    @match_regex('^!help morphovum')
    async def help_morphovum(self, event):
        '''
        Return help string to user
        '''
        text = 'Usage:<br>'
        text += '<b>!mo m ls .</b> | Look around base music directory<br>'
        text += '<b>!mo a toggle</b> | Toggle playing of ambience<br>'
        text += '<b>!mo m lsp rock/stoner</b> | Cue everything in rock/stoner dir<br>'
        text += '<b>!mo m lsa electronic</b> | Add and shuffle everything from electronic to current playlist<br>'
        text += '<b>!s</b> | Return the current song<br>'
        text += '<b>!mo c now</b> | Schedule a clip to be played now<br>'
        text += 'See https://github.com/dud1337/MorphOvum for more'

        await event.respond(
            Message(
                text=text
            )
        )

