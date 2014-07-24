import os.path
import base64
import uuid
import hashlib
import json
import logging
from datetime import datetime
from apscheduler.scheduler import Scheduler

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado import gen
from tornado.options import define, options

import sockjs.tornado 
import bitcoinrpc

import psycopg2
import momoko

from MersenneTwister19937 import MersenneTwister19937

define("port", default=8891, help="Port to run the server on", type=int)
define("sql_host")
define("sql_port")
define("sql_db")
define("sql_user")
define("sql_password")
define("coin_host")
define("coin_port")
define("coin_user")
define("coin_password")
define("debug_mode", default=True)
define("walletpassword")

app = None

def json_serial(obj):
    if isinstance(obj, datetime):
        serial = obj.strftime('%Y-%m-%d %H:%M:%S')
    return serial

def get_sql_datetime():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

class ServerVariables(object):
    serverseed = None
    hashedserverseed = None
    serverseedtime = None
    houseedge = 2;
    maxbetlimit = 0;
    bankaccount = "coinbank"
    db_string = None
    clients = None
    
    def __init__(self, db_string):
        self.db_string = db_string
        self.generate_server_seed()
        
    def register_clients(self, clients):
        self.clients = clients

    def generate_server_seed(self):
        self.serverseed = uuid.uuid4().hex
        self.hashedserverseed = hashlib.sha512(self.serverseed).hexdigest()
        self.serverseedtime = get_sql_datetime()
        query = 'insert into server_seeds (server_seed, hashed_server_seed, start_time) values (%s, %s, %s);'
        try:
            conn = psycopg2.connect(self.db_string)
            cur = conn.cursor()
            cur.execute(query, (self.serverseed, self.hashedserverseed, self.serverseedtime))
            conn.commit()
            if self.clients is not None:
                for client in self.clients:
                    client.broadcast_serverseedhash()
                    break
        except Exception, e:
            logging.exception(e)
        finally:
            conn.close()
        
        return self.serverseed, self.hashedserverseed
            
    def broadcast_bet_stats(self, betid=None):
        for client in self.clients:
            client.broadcast_bet_stats(betid)
            break

class Application(tornado.web.Application):
    def __init__(self):
        SockRouter = sockjs.tornado.SockJSRouter(ServerStatusHandler, '/status')
        handlers = [
            (r'/', IndexHandler),
            (r'/signup', SignupHandler),
            (r'/roll', RollDiceHandler),
            (r'/login', LoginHandler),
            (r'/logout', LogoutHandler),
            (r'/withdraw', WithdrawHandler),            
            (r'/verify', VerifyHandler),
            (r'/bets', BetSearchHandler),
            (r'/bets/', BetSearchHandler),
		] + SockRouter.urls
        settings = dict(
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret = 'sGwf4aZzT+aqNXMRPVWXw0bcKqU6Ek1PsHDfz6it/3s=', #base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes),
            login_url = "/login",
            xsrf_cookies = True,
            debug=options.debug_mode,
        )
        tornado.web.Application.__init__(self, handlers, **settings)

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")

    def get_cdn_host_name(self):
        return 'cdn.supercrypt.co'
 
    def is_cdn_enabled(self):
        return not options.debug_mode
 
    def static_url(self, path, include_host=None, **kwargs):
        if self.is_cdn_enabled():      
            relative_url = super(BaseHandler, self).static_url(path, include_host=False, **kwargs)
            return '//' + self.get_cdn_host_name() + relative_url
        else:
            return super(BaseHandler, self).static_url(path, include_host=include_host, **kwargs)

    @property
    def db(self):
        return self.application.db

    @property
    def server_variables(self):
        return self.application.server_variables

    @property
    def scheduler(self):
        return self.application.scheduler

    @property
    def coindaemon(self):
        return self.application.coindaemon

class VerifyHandler(BaseHandler):
    def get(self):
        self.render('verifier.html')
		
class IndexHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        username = None
        serverseedhash = None
        wallet_address = None

        if self.current_user:
            username = tornado.escape.json_decode(self.current_user).lower()
            serverseedhash = self.server_variables.hashedserverseed
            query = 'select wallet_address from users where username = lower(%s);'
        
            try:
                cursor = yield momoko.Op(self.db.execute, query, (username,), cursor_factory=psycopg2.extras.DictCursor)
                wallet_address = cursor.fetchone()['wallet_address']
                self.set_status(200)
            except Exception:
                logging.exception("Username: " + username)

        self.render('index.html', username=username, depositaddress=wallet_address, houseedge=self.server_variables.houseedge, jscode=None)

class SignupHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        jscode = "$(document).ready(function(){$('#signupModal').foundation('reveal', 'open')});"
        self.render('index.html', username=None, depositaddress=None, houseedge=self.server_variables.houseedge, jscode=jscode)

    @gen.coroutine
    def post(self):
        username = json.loads(self.get_argument("username", None)).lower()
        password = json.loads(self.get_argument("password", None))
        email = json.loads(self.get_argument("email", None))
        walletaddress = self.coindaemon.getnewaddress(username)
        hashedpassword, salt = hash_password(password)
        query = 'insert into users (username, hashed_password, salt, email, wallet_address) values (lower(%s), %s, %s, lower(%s), %s);'
        
        try:
            adduser = yield momoko.Op(self.db.execute, query, (username, hashedpassword, salt, email, walletaddress))
            set_current_user(self, username)
            self.set_status(200)
        except Exception:
            logging.exception("Username: " + username + " | Password: " + password + " | Email: " + email + " | Wallet Address: " + walletaddress)
            self.set_status(400, "Username or email is already in use. Please try a different username or email.")           
        finally:
            self.finish()
	
class LoginHandler(BaseHandler):
    def get(self):
        self.redirect(u"/")

    @gen.coroutine
    def post(self):
        username = json.loads(self.get_argument("username", None)).lower()
        password = json.loads(self.get_argument("password", None))

        if not username or not password:
            self.set_status(401, "No username or password.")
            self.finish()
            return

        query = 'select hashed_password, salt from users where username = lower(%s);'
        
        try:
            cursor = yield momoko.Op(self.db.execute, query, (username,), cursor_factory=psycopg2.extras.DictCursor)
            data = cursor.fetchone()
            auth = verify_password(password, data['hashed_password'], data['salt'])
            if auth:
                set_current_user(self, username)
                self.set_status(200, "%s authenticated." %(username))
            else:
                self.set_status(401, "Wrong username or password.")
        except Exception:
            logging.exception("Username: " + username)
            self.set_status(400)
        finally:
            self.finish()
				
class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect(u"/")
		
class WithdrawHandler(BaseHandler):
    def get(self):
        self.redirect(u"/")

    @gen.coroutine
    def post(self):
        if not self.current_user:
            self.set_status(403, "Forbidden. Please log in first.")
            return

        withdraw_address = json.loads(self.get_argument("withdrawAddress", None))
        username = tornado.escape.json_decode(self.current_user)
        withdraw_amount_str = json.loads(self.get_argument("withdrawAmount", None))
        withdraw_amount = None
        try:
            withdraw_amount = float(withdraw_amount_str)
        except Exception:
            logging.exception("Withdraw Address: " + withdraw_address + " | Username: " + username + " | Withdraw Amount: " + withdraw_amount_str)
            self.set_status(400, "Invalid amount to withdraw.")
            self.finish()
            return
        
        if not self.coindaemon.validateaddress(withdraw_address).isvalid:
            logging.info("[Invalid Withdraw Address] Withdraw Address: " + withdraw_address + " | Username: " + username + " | Withdraw Amount: " + withdraw_amount_str)
            self.set_status(400, "Invalid withdraw address. Please enter a valid value.")
            self.finish()
            return        

        if float(self.coindaemon.getbalance(username, minconf=2)) < withdraw_amount:
            logging.info("[Insufficient Funds] Withdraw Address: " + withdraw_address + " | Username: " + username + " | Withdraw Amount: " + withdraw_amount_str)
            self.set_status(400, "Insufficient funds to withdraw.")
            self.finish()
            return

        transaction_time = get_sql_datetime()
        
        try:
            try:
                self.coindaemon.walletpassphrase(options.walletpassword, 60)
            except bitcoinrpc.exceptions.WalletAlreadyUnlocked:
                pass
            transaction_id = self.coindaemon.sendfrom(username, withdraw_address, withdraw_amount, minconf=2, comment="Supercrypt COIN Dice Withdraw")
            query = 'insert into transactions (transaction_id, transaction_type, transaction_time, username, amount, withdraw_address) values (%s, %s, %s, %s, %s, %s);'
            addtransaction = yield momoko.Op(self.db.execute, query, (transaction_id, "withdraw", transaction_time, username, withdraw_amount, withdraw_address))
            balance = self.coindaemon.getbalance(username, minconf=2)
            self.write(dict(bal=str(balance)))
            self.set_status(200)
        except Exception:
            logging.exception("Transaction ID: " + transaction_id + " | Username: " + username + " | Withdraw Address: " + withdraw_address + " | Withdraw Amount: " + withdraw_amount_str + " | Balance: " + str(balance))
            self.set_status(400, "Error withdrawing.")    
        finally:
            self.finish()

class RollDiceHandler(BaseHandler):
    def get(self):
        self.redirect(u"/")

    @gen.coroutine
    def post(self):
        if not self.current_user:
            self.set_status(403, "Forbidden. Please log in first.")
            return
        
        bet_amount = json.loads(self.get_argument("betAmount", None))
        win_chance = json.loads(self.get_argument("winChance", None))
        client_seed = json.loads(self.get_argument("clientSeed", None))
        game_type = json.loads(self.get_argument("gameType", None))
        username = tornado.escape.json_decode(self.current_user)
        query = 'select max(bet_id) as rollnumber from bets;'

        try:
            cursor = yield momoko.Op(self.db.execute, query, cursor_factory=psycopg2.extras.DictCursor)
            rollnumber = cursor.fetchone()['rollnumber']
            if rollnumber is None:
                rollnumber = 1
            else:
                rollnumber = int(rollnumber) + 1
            win, rolled = decide_game(game_type, win_chance, self.server_variables.serverseed, client_seed, rollnumber)
            bet_time = get_sql_datetime()
        except Exception:
            logging.exception("Bet Amount: " + bet_amount + " | Win Chance: " + win_chance + " | Client Seed: " + client_seed + " | Game Type: " + game_type + " | Username " + username)
            self.set_status(400, "Unknown bet type.")
            self.finish()
            return
        else:
            balance = float(self.coindaemon.getbalance(username, minconf=2))
            bet_amount_real = float(bet_amount)
            
            if balance < bet_amount_real or bet_amount_real < 0:
                self.set_status(400, "Insufficient funds.")
                return
        
            try:
                payout = round(((100-self.server_variables.houseedge)/float(win_chance)), 4)
                profit = (bet_amount_real * payout) - bet_amount_real
                if profit > self.server_variables.maxbetlimit:
                    self.set_status(400, "Exceeded maximum amount allowed.")
                    return
                if profit < 0.00000001:
                    self.set_status(400, "Profit less than minimum amount possible.")
                    return
                profit = round(profit, 8)
                result = ""
                query = 'insert into bets (username, bet_time, bet_amount, payout, game, roll, profit, result, server_seed, client_seed) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning bet_id;'
                if win:
                    self.coindaemon.move(self.server_variables.bankaccount, username, profit, minconf=2, comment="COIN Dice.")
                    message = "Congratulations! You rolled %s and won the dice roll!" %(rolled)
                    result = "win"
                else:
                    self.coindaemon.move(username, self.server_variables.bankaccount, bet_amount_real, minconf=2, comment="COIN Dice.")
                    profit = bet_amount_real * -1
                    message = "Oops! You rolled %s. Better luck next time!" %(rolled)
                    result = "lose"
                balance = self.coindaemon.getbalance(username, minconf=2)
                self.server_variables.maxbetlimit = float(self.coindaemon.getbalance(self.server_variables.bankaccount)) * 0.01

                try:
                    cursor = yield momoko.Op(self.db.execute, query, (username, bet_time, bet_amount, payout, game_type, rolled, profit, result, self.server_variables.serverseed, client_seed), cursor_factory=psycopg2.extras.DictCursor)
                    self.set_status(200)
                    bet_id = cursor.fetchone()['bet_id']
                    self.set_status(200)
                    self.write(dict(message=message, bal=str(balance), result=result))
                    self.server_variables.broadcast_bet_stats(bet_id)
                except Exception:
                    logging.exception("Username: " + username + " | Profit: " + str(profit) + " | Bet Amount: " + bet_amount + " | Result: " + result)
                    self.set_status(400, "Error inserting transaction into database.")                
            except Exception:
                logging.exception("Username: " + username + " | Profit: " + str(profit) + " | Bet Amount: " + bet_amount + " | Result: " + result)
                self.set_status(400, "Invalid values submitted.")
        finally:
            self.finish()
            
class BetSearchHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        search_param = self.get_argument("q", None)
        output = self.get_argument("output", None)
        
        if search_param is None:
            self.render("bets.html", results=None)
            return
            
        if search_param.isdigit():
            query = 'select bet_id, username, bet_time, bet_amount, payout, game, roll, profit, result, server_seed, client_seed from bets where bet_id = %s AND server_seed != %s order by bet_id desc;'
        else:
            query = 'select bet_id, username, bet_time, bet_amount, payout, game, roll, profit, result, server_seed, client_seed from bets where username = lower(%s) AND server_seed != %s order by bet_id desc;'

        try:
            cursor = yield momoko.Op(self.db.execute, query, (search_param, self.server_variables.serverseed), cursor_factory=psycopg2.extras.DictCursor)
            data = [dict((cursor.description[i][0], value) \
                for i, value in enumerate(row)) for row in cursor.fetchall()]
            msg = '{"searchResults":%s}' % (json.dumps(data, default=json_serial))
            
            if output == "json":
                self.write(msg)
                self.finish()
            else:
                self.render("bets.html", results=json.dumps(data, default=json_serial))
        except Exception:
            logging.exception("Search Parameter: " + search_param)
            self.set_status(400, "Unknown search parameter.")

    def post(self):        
        self.redirect(u"/bets")
            
class BaseSocketHandler(sockjs.tornado.SockJSConnection):
    @property
    def db(self):
        return app.db

    @property
    def server_variables(self):
        return app.server_variables

    @property
    def scheduler(self):
        return app.scheduler

    @property
    def coindaemon(self):
        return app.coindaemon
            
class ServerStatusHandler(BaseSocketHandler):
    clients = set()

    def on_open(self, request):
        self.clients.add(self)
        if self.server_variables.clients is None:
            self.server_variables.register_clients(self.clients)
        self.server_variables.maxbetlimit = float(self.coindaemon.getbalance(self.server_variables.bankaccount)) * 0.01
        self.send_serverseedhash()
        self.send_bet_stats()
        
    def on_message(self, message):
        self.update_client(message)

    def on_close(self):
        try:
            self.clients.remove(self)
        except ValueError:
            pass
	
    def send_serverseedhash(self):
        self.send(self.get_serverseedhash())
        
    def broadcast_serverseedhash(self):
        self.broadcast(self.clients, self.get_serverseedhash())
        
    def get_serverseedhash(self):
        msg = '{"type":"%s", "serverSeedHash":"%s"}' % ("seed", self.server_variables.hashedserverseed)
        return msg
        
    @gen.coroutine
    def send_bet_stats(self, betid=None):
        query_total_wager = 'select sum(bet_amount) as totalwager from bets;'
        query_total_bets = 'select count(*) as totalbets from bets;'
        query_history = 'select bet_id, username, bet_time, bet_amount, payout, game, roll, profit, result from bets order by bet_id desc limit 30;'
        if betid is not None:
            query_history = 'select bet_id, username, bet_time, bet_amount, payout, game, roll, profit, result from bets where bet_id = %s;'
        try:
            self.db.execute(query_total_wager, cursor_factory=psycopg2.extras.DictCursor, callback=(yield gen.Callback('query_total_wager')))
            self.db.execute(query_total_bets, cursor_factory=psycopg2.extras.DictCursor, callback=(yield gen.Callback('query_total_bets')))
            if betid is None:
                self.db.execute(query_history, cursor_factory=psycopg2.extras.DictCursor, callback=(yield gen.Callback('query_history')))
            else:
                self.db.execute(query_history, (betid,), cursor_factory=psycopg2.extras.DictCursor, callback=(yield gen.Callback('query_history')))        
            cursor_total_wager, cursor_total_bets, cursor_history = yield momoko.WaitAllOps(('query_total_wager', 'query_total_bets', 'query_history'))
            total_wager = cursor_total_wager.fetchone()['totalwager']
            total_bets = cursor_total_bets.fetchone()['totalbets']
            bet_history = cursor_history.fetchall()
            msg = '{"type":"%s", "totalWagered":"%s", "totalBets":"%s", "maxBetLimit":"%s", "betHistory":%s}' % ("stats", total_wager, total_bets, self.server_variables.maxbetlimit, json.dumps(bet_history, default=json_serial))
            self.send(msg)
        except Exception:
            logging.exception(e)
        
    @gen.coroutine
    def broadcast_bet_stats(self, betid=None):
        query_total_wager = 'select sum(bet_amount) as totalwager from bets;'
        query_total_bets = 'select count(*) as totalbets from bets;'
        query_history = 'select bet_id, username, bet_time, bet_amount, payout, game, roll, profit, result from bets order by bet_id desc limit 30;'
        if betid is not None:
            query_history = 'select bet_id, username, bet_time, bet_amount, payout, game, roll, profit, result from bets where bet_id = %s;'
        try:
            self.db.execute(query_total_wager, cursor_factory=psycopg2.extras.DictCursor, callback=(yield gen.Callback('query_total_wager')))
            self.db.execute(query_total_bets, cursor_factory=psycopg2.extras.DictCursor, callback=(yield gen.Callback('query_total_bets')))
            if betid is None:
                self.db.execute(query_history, cursor_factory=psycopg2.extras.DictCursor, callback=(yield gen.Callback('query_history')))
            else:
                self.db.execute(query_history, (betid,), cursor_factory=psycopg2.extras.DictCursor, callback=(yield gen.Callback('query_history')))        
            cursor_total_wager, cursor_total_bets, cursor_history = yield momoko.WaitAllOps(('query_total_wager', 'query_total_bets', 'query_history'))
            total_wager = cursor_total_wager.fetchone()['totalwager']
            total_bets = cursor_total_bets.fetchone()['totalbets']
            bet_history = cursor_history.fetchall()
            msg = '{"type":"%s", "totalWagered":"%s", "totalBets":"%s", "maxBetLimit":"%s", "betHistory":%s}' % ("stats", total_wager, total_bets, self.server_variables.maxbetlimit, json.dumps(bet_history, default=json_serial))
            self.broadcast(self.clients, msg)
        except Exception:
            logging.exception()

    def update_client(self, username):
        balance = self.coindaemon.getbalance(username, minconf=2)
        self.send('{"type":"%s", "clientBalance":"%s"}' % ("client", balance))

def decide_game(gametype, underamount, serverseed, clientseed, rollnumber):
    rolled = roll_dice(serverseed, clientseed, rollnumber)
    if gametype == "under":
        return (float(rolled) < float(underamount)), rolled
    elif gametype == "over":
        overamount = 100 - float(underamount)
        return (float(rolled) > float(overamount)), rolled
    else:
        raise Exception("Invalid bet type.")
    
def roll_dice(serverseed, clientseed, rollnumber):
    hashed_result = hashlib.sha512(serverseed + clientseed + str(rollnumber)).hexdigest()
    mt = MersenneTwister19937(int(hashed_result[-8:], 16))
    return round(mt.genrand_real1() * 100,2)

def set_current_user(self, user):
    if user:
        self.set_secure_cookie("user", tornado.escape.json_encode(user), httponly=True)
    else:
        self.clear_cookie("user")

def hash_password(password, salt=None):
    if salt is None:
        salt = uuid.uuid4().hex
    hashed_password = hashlib.sha512(password + salt).hexdigest()
    return (hashed_password, salt)
 
def verify_password(password, hashed_password, salt):
    re_hashed, salt = hash_password(password, salt)
    return re_hashed == hashed_password

def main():
    tornado.options.parse_config_file(os.path.join(os.path.dirname(__file__), "config.py"))
    tornado.options.parse_command_line()
    db_string = 'dbname=%s user=%s password=%s host=%s port=%s' % (options.sql_db, options.sql_user, options.sql_password, options.sql_host, options.sql_port)
    
    if options.debug_mode:
        db_string = 'dbname=%s user=%s password=%s host=%s port=%s' % ('supercryptdb', 'postgres', 'password', '127.0.0.1', '5432')
    
    global app
    app = Application()
    app.db = momoko.Pool(
        dsn = db_string,
        size = 1
    )
    app.server_variables = ServerVariables(db_string)
    app.scheduler = Scheduler()
    app.scheduler.start()
    app.scheduler.add_cron_job(app.server_variables.generate_server_seed, day='*', hour='0', minute='0')
    app.coindaemon = bitcoinrpc.connect_to_remote(options.coin_user, options.coin_password, host=options.coin_host, port=options.coin_port)
    app.server_variables.maxbetlimit = float(app.coindaemon.getbalance(app.server_variables.bankaccount)) * 0.01    
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
	main()