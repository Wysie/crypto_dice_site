# Bitcoin and Other Cryptocurrencies Dice Site

## Introduction
This is a fair dice site including the verifier so you can see that the results are fair and not tampered with. I wrote this as a way for me to learn Tornado. In addition, I'm using KnockoutJS, jQuery, Foundation and SockJS. Lots of other Python libraries were used too, such as bitcoin-python to handle the RPC calls to the coin daemon. Database-wise, it's running off PostgreSQL, using momoko to connect to it from Tornado for async DB calls.

I'm also using a custom Mersenne Twister (that is in line with the JavaScript libraries I'm using) so that the server and client can both generate the same random numbers using the same seed. The default Python RNG (which is using Mersenne Twister) does not give me the same results as the client and seems to depends on the Python version and the machine I'm running it on. I found the Mersenne Twister source online but can't remember where, please reach out to me if you are the author or if you know where it comes from, thank you.

Here is one of the sites I have running this code: http://coindice.supercrypt.co.

As I'm no longer actively maintaining those sites, I decided to put this up on Github publicly in case anyone is interested. Have fun :)! Just for information, most of the content still references Aiden dice, which is one of the latest dice sites I've built.

Please reach out to me on Twitter [@Wysie_Soh](https://twitter.com/Wysie_Soh/) if you have any questions.

## Getting Started
Please make sure you have the following:
- PostgreSQL
- Python 2.7.x
- pip
- Bitcoin or alt coin binary (usually I compile it from source)

Once you have all of the above, you can then install all other required Python libraries with:

    pip install -r requirements.txt

You will also need to create a database in PostgreSQL, and create the tables as listed in tables.txt.

### Coin Daemon
Please make sure you have a compiled version of Bitcoin or the altcoin as well. Refer to the respective coins' README for instructions on compiling. That is not within the scope of this README.

## Configuration

### Coin Daemon
Start your coin daemon and create a new account and give it a name, e.g. "bitcoinbank". I think accounts will be deprecated in future but I made use of it for this project. See [here](https://en.bitcoin.it/wiki/Accounts_explained) for more information.

### Server
Most of the set up can be configured in config.py and is self-explanatory.

There are, however, a few variables to change elsewhere and they are as follows.

#### main.py
Look for this line:

    bankaccount = "coinbank"

Rename "coinbank" to the account you created, e.g. "bitcoinbank"

There are a few CDN-related definitions in the file, you may need to edit the code to disable using a CDN, and also to change the CDN address.

#### HTML files in templates/
More for aesthetic reasons and does not actually affect the function. All templates extend from base.html.

## Get It Running
Once you have completed all of the above steps, you can simply run it with:

    python main.py

And then access it at http://hostaddress:port.

## Deploying with nginx and Supervisor
I use nginx to serve the pages, and Supervisor to start the server and the coin daemon. Supervisor also allows me to run multiple dice sites (servers and coin daemons) on a single virtual/physical server. I won't be covering this portion for now and may do so in a future update. Chase Lee has an excellent article on setting up Supervisor and nginx [here](http://chase.io/post/17197274701/).