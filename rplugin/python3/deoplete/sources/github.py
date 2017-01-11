import netrc
import re
import json
import base64
from subprocess import Popen, PIPE
import urllib.request as request
from urllib.parse import urlparse
from deoplete.source.base import Base
from deoplete.util import error


class Source(Base):

    def __init__(self, vim):
        """
        Base init
        """
        Base.__init__(self, vim)

        self.name = 'github'
        self.mark = '[GH]'
        self.filetypes = ['gitcommit', 'magit']
        self.debug_enabled = True
        self.input_pattern = '#'

    def log(self, message):
        """
        Log message to vim echo
        """
        self.debug('*' * 10)
        self.debug(message)
        self.debug('*' * 10)

    def repo_homepage(self):
        """Return the repo homepage, akin to rhubarb#repo_request
        function
        :returns: String like "https://github.com/user/repo"
        """
        proc = Popen(["git", "config", "--get",
                      "remote.origin.url"], stdout=PIPE)
        out, err = proc.communicate()

        if err is not None:
            error(self.vim, 'Theres been an error')
        repoConfig = str(out.decode('utf-8'))

        if 'https' in repoConfig:
            self.log('repoConfig: ' + repoConfig)
            url_fragments = repoConfig.strip(".git\n")
            homepage = url_fragments
        else:
            url_fragments = repoConfig.strip("git\n").strip('.').split(':')
            homepage = 'https://github.com/' + url_fragments[1]
        return homepage

    def repo_base(self):
        """
        :returns: API endpoint for current repo
        """
        base = self.repo_homepage()
        if base:
            if re.search('//github\.com/', base) is not None:
                base = base.replace('//github.com/', '//api.github.com/repos/')
            else:
                # I'm not sure how to work this
                # It's enterprise github, I don't understand vim regex
                base = "failure"
                pass

        return base

    def authenticator(self, hostname):
        """Parse netrc file into a dict

        :hostname: Hostname to get authenticator for
        :returns: Dict with login, account and password key

        """
        myrc = netrc.netrc()
        authenticator = myrc.authenticators(hostname)

        return {'login': authenticator[0],
                'account': authenticator[1],
                'password': authenticator[2]}

    def get_complete_position(self, context):
        """
        returns the cursor position
        """
        m = re.search(r"\w*$", context["input"])
        return m.start() if m else -1

    def gather_candidates(self, context):
        """Gather candidates from github API
        """

        base = self.repo_base()
        if base:
            base = base + '/issues?per_page=200'

            base_url = urlparse(base)
            credentials = self.authenticator(base_url.hostname)

            r = request.Request(base)
            creds = base64.encodestring(bytes('%s:%s' % (credentials.get(
                'login'), credentials.get('password')), 'utf-8')).strip()
            r.add_header('Authorization', 'Basic %s' % creds.decode('utf-8'))

            with request.urlopen(r) as req:
                response_json = req.read().decode('utf-8')
                response = json.loads(response_json)

                titles = [x.get('title', '') for x in response]
                numbers = [{'word': str(x.get('number', '')),
                            'menu': x.get('title')
                            }
                           for x in response]
                return numbers
        return []
