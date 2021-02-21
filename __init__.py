######################################################################
#   
#   MorphOvum Opsdroid
#   Interacting with MorphOvum api via Opsdroid
#   
######################################################################
from opsdroid.skill import Skill
from opsdroid.matchers import match_regex, match_crontab, match_event
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

    def auth(self):
        self.session.post(
            self.config.get('morphovum_api_link') + 'admin',
            data={
                'password_hash':sha256(self.config.get('morphovum_admin_cred').encode('utf-8')).hexdigest()
            }
        )

    def append_webpage(self, text):
        return text + ' 🎵 ' + self.config.get('morphovum_webpage_link') + ' 🎵' 

    @match_crontab('30 */3 * * *', timezone="Europe/Zurich")
    async def say_song(self, event):
        song_data = json.loads(self.session.get(self.config.get('morphovum_api_link') + 'music/current/track').text)
        if song_data['msg'] == 'ok!':
            msg =  sself.append_webpage(song_data['data'])
        else:
            msg = 'Error: ' + str(song_data)

        await self.opsdroid.send(
            Message(
                text=msg,
                target=self.config.get('room_music')
            )
        )

    @match_regex('^!s$')
    async def say_song(self, message):
        song_data = json.loads(self.session.get(self.config.get('morphovum_api_link') + 'music/currenttrack').text)
        if song_data['msg'] == 'ok!':
            msg =  self.append_webpage(song_data['data'])
        else:
            msg = 'Error: ' + str(song_data)

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

            await message.respond(
                Message(
                    text=self.append_webpage(str(output))
                )
            )