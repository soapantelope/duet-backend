import cortex
from cortex import Cortex

import singlestoredb as s2
from dotenv import load_dotenv
import os

load_dotenv()

SINGLESTORE_HOST = os.getenv('SINGLESTORE_HOST')
SINGLESTORE_USER = os.getenv('SINGLESTORE_USER')
SINGLESTORE_PORT = os.getenv('SINGLESTORE_PORT')
SINGLESTORE_DATABASE = os.getenv('SINGLESTORE_DATABASE')
SINGLESTORE_PASSWORD = os.getenv('SINGLESTORE_PASSWORD')

conn = s2.connect(f'{SINGLESTORE_USER}:{SINGLESTORE_PASSWORD}@{SINGLESTORE_HOST}:{SINGLESTORE_PORT}/{SINGLESTORE_DATABASE}')


class LivePowerBands():
    """
    A class to show band power data (theta, alpha, beta, etc.) in live mode.
    
    Attributes
    ----------
    c : Cortex
        Cortex communicate with Emotiv Cortex Service

    Methods
    -------
    start():
        To start a live band power process from starting a websocket
    subscribe_data():
        To subscribe to power band data stream
    """
    def __init__(self, app_client_id, app_client_secret, **kwargs):
        self.c = Cortex(app_client_id, app_client_secret, debug_mode=True, **kwargs)
        self.c.bind(create_session_done=self.on_create_session_done)
        self.c.bind(new_pow_data=self.on_new_pow_data)
        self.c.bind(inform_error=self.on_inform_error)

    def start(self, headsetId=''):
        """
        To start live process as below workflow
        (1) check access right -> authorize -> connect headset -> create session
        (2) subscribe 'pow' data to show live band power data
        
        Parameters
        ----------
        headsetId: string, optional
             id of wanted headset which you want to work with it.
             If the headsetId is empty, the first headset in list will be set as wanted headset
        """
        if headsetId != '':
            self.c.set_wanted_headset(headsetId)

        self.c.open()

    def subscribe_data(self, streams):
        """
        To subscribe to one or more data streams
        'pow': Band Power
        
        Parameters
        ----------
        streams : list, required
            list of streams. For example, ['pow']

        Returns
        -------
        None
        """
        self.c.sub_request(streams)

    # callbacks functions
    def on_create_session_done(self, *args, **kwargs):
        print('Session created')
        # Subscribe to band power stream
        stream = ['pow']
        self.subscribe_data(stream)

    def on_new_pow_data(self, *args, **kwargs):
        """
        To handle band power data emitted from Cortex
        
        Returns
        -------
        data: dictionary
            the format such as
            {'pow': [0.5, 0.6, 0.7, 0.4, 0.3, 0.2, 0.1, 0.3], 'time': 1590736942.8479}
            where the pow array represents [theta, alpha, lowBeta, highBeta, gamma] values
            for each channel
        """
        data = kwargs.get('data')
        
        # Calculate the average alpha and beta values
        alpha = 0
        beta = 0
        for node in range(14):
            alpha += data['pow'][node * 5 + 1]
            beta += (data['pow'][node * 5 + 2] + data['pow'][node * 5 + 3]) / 2
        
        avg_alpha = alpha / 14
        avg_beta = beta / 14
        
        # Prepare the data for insertion
        sql = "INSERT INTO brain_wave_data (avg_alpha, avg_beta) VALUES (%s, %s)"
        values = (avg_alpha, avg_beta)

        try:
            # Use the established connection to execute the SQL command
            with conn.cursor() as cursor:
                cursor.execute(sql, values)
                conn.commit()  # Commit the transaction
        except Exception as e:
            print("Error uploading data to SingleStore: {}".format(e))

        # Print the values (optional)
        print("Average Alpha: {}, Average Beta: {}".format(avg_alpha, avg_beta))


    def on_inform_error(self, *args, **kwargs):
        error_data = kwargs.get('error_data')
        error_code = error_data['code']
        error_message = error_data['message']

        print(error_data)

        if error_code == cortex.ERR_PROFILE_ACCESS_DENIED:
            print('Get error ' + error_message + ". Disconnect headset to fix this issue for next use.")
            self.c.disconnect_headset()


# -----------------------------------------------------------
# 
# GETTING STARTED
#   - Please reference to https://emotiv.gitbook.io/cortex-api/ first.
#   - Connect your headset with dongle or bluetooth. You can see the headset via Emotiv Launcher
#   - Please make sure the your_app_client_id and your_app_client_secret are set before starting running.
#   - The power bands data includes theta (4-8 Hz), alpha (8-12 Hz), low beta (12-16 Hz), 
#     high beta (16-25 Hz), and gamma (25-45 Hz) for each channel
# RESULT
#    You will receive live band power data in the format:
#    {'pow': [0.5, 0.6, 0.7, 0.4, 0.3, 0.2, 0.1, 0.3], 'time': 1647525819.0223}
# 
# -----------------------------------------------------------

def main():
    # Please fill your application clientId and clientSecret before running script
    your_app_client_id = os.getenv('EMOTIV_CLIENT_ID')
    your_app_client_secret = os.getenv('EMOTIV_CLIENT_SECRET')

    # Init live power bands
    l = LivePowerBands(your_app_client_id, your_app_client_secret)
    
    # Start the session
    l.start()

if __name__ =='__main__':
    main()