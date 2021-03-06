tornado-putmetric
=================

Asynchronous implementation of Amazon CloudWatch PutMetric call for Tornado Web

This code is licensed under the Apache Licence, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0.html).

Overview
--------

There are two classes
* `TornadoCloudWatch` -- simple class sending metric one by one 
* `BatchingTornadoCloudWatch` -- periodically sends metrics in batches of up to 20; use one instance per app

Typically you'd use `BatchingTornadoCloudWatch`. Since CloudWatch has only 1 minute resolution, there is no need to send metric more often than that, thus `BatchingTornadoCloudWatch` will gather metric and send them periodically (by default once per minute) in batches.


Usage
-----

Very simple usage example. Skipped the exception handling, to keep the example concise. 

    import tornado.ioloop
    import tornado.web
    from tornado_putmetricdata import TornadoCloudWatchException, BatchingTornadoCloudWatch 

    class MainHandler(tornado.web.RequestHandler):
        def get(self):
            self.write("Hello, world")
            self.application.cloudwatch.put_metric_data("MyHelloWorldNamespace", 
                                                        [{'name': metric_name, 
                                                          'value': value,
                                                          'unit': unit,
                                                          'dimensions': [{'name': dimension_name,
                                                                          'value': dimension_value}],
                                                        }])


    application = tornado.web.Application([
        (r"/", MainHandler),
    ])

    if __name__ == "__main__":
        application.listen(8888)
        
        application.cloudwatch = BatchingTornadoCloudWatch(region=AWS_REGION_NAME,
                                                           access_key_id=AWS_ACCESS_KEY_ID, 
                                                           secret_access_key=AWS_SECRET_ACCESS_KEY)
        
        tornado.ioloop.IOLoop.instance().start()





