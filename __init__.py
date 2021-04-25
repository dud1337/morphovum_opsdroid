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
from time import time, sleep

import datetime
import json
import requests
import sched
from hashlib import sha256

class MorphOvumSkill(Skill):
    def __init__(self, *args, **kwargs):
        super(MorphOvumSkill, self).__init__(*args, **kwargs)
        self.session = requests.Session()
        self.auth()
        self.api_methods = json.loads(self.session.get(self.config.get('morphovum_api_link') + '/help').text)['data']

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
        if event.target == self.config.get('room_music'):
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

    def append_webpage(self, text):
        return '🎵 ' + self.config.get('morphovum_webpage_link') + ' 🎵 ' + text + ' 🎵'

    
    @match_regex('^!mo reauth$')
    async def re_auth(self, message):
        self.auth()

    @match_crontab('38 1 * * *', timezone="Europe/Zurich")
    @match_crontab('20 16 * * *', timezone="Europe/Zurich")
    async def say_song_interval(self, event):
        song_data = json.loads(self.session.get(self.config.get('morphovum_api_link') + 'music/currenttrack').text)
        if song_data['err']:
            msg = 'Error: ' + song_data['msg']
        else:
            msg =  self.append_webpage(song_data['msg'])

        await self.avoid_spam_send(
            Message(
                text=msg,
                target=self.config.get('room_music')
            )
        )

    @match_regex('^!s$')
    async def say_song(self, message):
        song_data = json.loads(self.session.get(self.config.get('morphovum_api_link') + 'music/currenttrack').text)
        if song_data['err']:
            msg = 'Error: ' + str(song_data['msg'])
        else:
            msg =  self.append_webpage(song_data['msg'])

        await message.respond(
            Message(
                text=msg
            )
        )

    @match_regex('^!mo (?P<player>(a|ambience)|(m|music)|(c|clips))[ _]{1}(?P<command>[\w_]+) ?(?P<arg>\S+)?$')
    async def api_request(self, message):
        api_call = ''

        player = message.entities['player']['value']
        if player in {'m', 'music'}:
            api_call += 'music_'
        elif player in {'a', 'ambience'}:
            api_call += 'ambience_'
        else: # player in {'c', 'clips'}
            api_call += 'clips_'

        api_call += message.entities['command']['value']

        if api_call in self.api_methods:
            url = self.config.get('morphovum_api_link') + api_call.replace('_', '/')
            if self.api_methods[api_call]['arg']:
                output = json.loads(self.session.post(
                    url,
                    data={
                        self.api_methods[api_call]['arg']:message.entities['arg']['value']
                    }
                ).text)
            else:
                output = json.loads(self.session.get(
                    url
                ).text)

            if output['err']:
                output = 'Error: ' + output['msg']
            else:
                output = output['msg']

            await message.respond(
                Message(
                    text=self.append_webpage(output)
                )
            )
