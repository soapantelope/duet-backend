import cortex
from cortex import Cortex

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
        # print('Band Power data: {}'.format(data))

        alpha = 0
        beta = 0
        for node in range(14):
            alpha += data['pow'][node * 5 + 1]
            beta += (data['pow'][node * 5 + 2] + data['pow'][node * 5 + 3]) / 2
        
        print(alpha / 14, beta / 14)

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
    your_app_client_id = 'JFnPljMcfueBxLeSWjJxfBCH43JBMNqSI2eNqCzM'
    your_app_client_secret = 'OIJ7kTaA6XughEgNJI9eENenKhcKlgiDTuYnIKCkxWjMQNEEYdXYHGOKNoH5wd59l7q90MxgisGw0smAhKtNqGE8PuemH55vQztJf6QCP0sytnKhPBSztOOk8rio88yQ'

    # Init live power bands
    l = LivePowerBands(your_app_client_id, your_app_client_secret)
    
    # Start the session
    l.start()

if __name__ =='__main__':
    main()