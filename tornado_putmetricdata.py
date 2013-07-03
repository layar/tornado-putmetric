import os
import hmac
import base64
import hashlib
from datetime import datetime
from urllib import urlencode, quote_plus

from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.ioloop import PeriodicCallback
from log import logging
log = logging.getLogger(__name__)

PUT_METRIC_CHUNK_SIZE = 20 ## "you can publish up to 20 data points in a single call to PutMetricData"

class TornadoCloudWatchException(Exception):
    pass

REGIONS = ( 'us-east-1',        # US East (Northern Virginia)
            'us-west-2',        # US West (Oregon)
            'us-west-1',        # US West (Northern California)
            'eu-west-1',        # EU (Ireland)
            'ap-southeast-1',   # Asia Pacific (Singapore)
            'ap-southeast-2',   # Asia Pacific (Sydney)
            'ap-northeast-1',   # Asia Pacific (Tokyo)
            'sa-east-1',        # South America (Sao Paulo)
            )
ENDPOINTS = { r:'monitoring.%s.amazonaws.com'%r for r in REGIONS}

class TornadoCloudWatch(object):
    """ utility class for sending metrics to CloudWatch
        uses Tornado's AsyncHTTPClient
    """
    

    
    def __init__(self, region, access_key_id=None, secret_access_key=None):
        if region not in REGIONS:
            raise TornadoCloudWatchException("unknown region")
        
        self.region = region
        self.endpoint = ENDPOINTS[region]
        
        self.access_key_id = access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        if not self.access_key_id:
            raise TornadoCloudWatchException("access_key_id missing")
        
        self.secret_access_key = secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        if not self.secret_access_key:
            raise TornadoCloudWatchException("secret_access_key missing")
    
    def __unicode__(self):
        return "TornadoCloudwatch: endpoint %s, account: %s"%(self.endpoint, self.access_key_id)
    
    def _get_signed_request(self, action, extra_params, timestamp=None, protocol="http"):
        """ sign an url using Signature Version 2
            http://docs.aws.amazon.com/general/latest/gr/signature-version-2.html
        """
        
        params = {'Action': action,
                  'AWSAccessKeyId': self.access_key_id,
                  'SignatureVersion': 2,
                  'SignatureMethod': 'HmacSHA256',
                  'Timestamp': (timestamp or datetime.now()).isoformat(),
                  'Version': '2010-08-01',
                  }
        params.update(extra_params)
        body = urlencode(sorted(params.items()))
        msg = 'POST\n%s\n/\n%s'%(self.endpoint,body)
        signature = hmac.new(key=self.secret_access_key, msg=msg, digestmod=hashlib.sha256).digest()
        signature = base64.encodestring(signature).strip()
        body += "&Signature=%s"%quote_plus(signature)
        request = HTTPRequest(url = "%s://%s/" % (protocol, self.endpoint), 
                              method="POST",
                              body=body)
        return request
    
    def _send_request(self, action, params=None, callback=None, timestamp=None):
        params = params or {}
        http_client = AsyncHTTPClient()
        http_client.fetch(self._get_signed_request(action, params, timestamp), callback)
    
    def put_metric_data(self, namespace, metrics, timestamp=None, callback=None):
        """ send one or more metrics to single namespace in CloudWatch 
            @param namespace
            @param metrics: dictionary of metric name:value  
        """
        
        action = 'PutMetricData'
        params = {'Namespace': namespace }
        if type(metrics) not in (list, tuple):
            metrics = (metrics,)
            
        for i, metric in enumerate(metrics,1):
            params['MetricData.member.%d.MetricName'%i] = metric['name']
            params['MetricData.member.%d.Value'%i] = metric['value']
            params['MetricData.member.%d.Unit'%i] = metric.get('unit','Count')
            dimensions = metric.get('dimensions',[])
            if dimensions and type(dimensions) not in (list, tuple):
                dimensions = (dimensions,)
            for j, dimension in enumerate(dimensions, 1):
                params['MetricData.member.%d.Dimensions.member.%d.Name'%(i,j)] = dimension['name']
                params['MetricData.member.%d.Dimensions.member.%d.Value'%(i,j)] = dimension['value']
            
        callback = callback or self._callback
        self._send_request(action, params, callback, timestamp)
        
    def _callback(self, response):
        if response.error:
            log.error(response)


class BatchingTornadoCloudWatch(TornadoCloudWatch):
    """ utility class for sending metrics to CloudWatch in batches
        uses Tornado's AsyncHTTPClient
        typically you'd want to use just one instance per application
    """
    def __init__(self, region, access_key_id=None, secret_access_key=None, frequency_miliseconds=60000): 
        super(BatchingTornadoCloudWatch, self).__init__(region, access_key_id, secret_access_key)
        self.metric_cache = {}
        PeriodicCallback(self.send_cached_metrics, frequency_miliseconds).start()
    
    @staticmethod
    def _minute_now(t=None):
        """Amazon CloudWatch aggregates the data to a minimum granularity of one minute. 
           This generates one minute granularity timestamps 
        """
        t = t or datetime.now()
        return datetime(*t.timetuple()[:5])
    
    def put_metric_data_now(self, *args, **kwargs):
        super(BatchingTornadoCloudWatch, self).put_metric_data(*args, **kwargs)
        
    def put_metric_data_later(self, namespace, metrics):
        if type(metrics) not in (list, tuple):
            metrics = (metrics,)
        self.metric_cache.setdefault((self._minute_now(),namespace), []).extend(metrics)
    
    ### keeping interface consistent, so it's a drop-in replacement for TornadoCloudWatch
    put_metric_data = put_metric_data_later
    
    def send_cached_metrics(self):
        cache_to_send, self.metric_cache = self.metric_cache, {}
        for (timestamp, namespace), metrics in cache_to_send.items():
            for metrics_chunk in [metrics[i:i+PUT_METRIC_CHUNK_SIZE] for i in range(0, len(metrics), PUT_METRIC_CHUNK_SIZE)]: 
                self.put_metric_data_now(namespace, metrics_chunk, timestamp)
