tornado-putmetric
=================

Asynchronous implementation of Amazon CloudWatch PutMetric call for Tornado Web


Overview
--------

There are two classes
* `TornadoCloudWatch` -- simple class sending metric one by one 
* `BatchingTornadoCloudWatch` -- periodically sends metrics in batches of up to 20; use one instance per app

Since CloudWatch has only 1 minute resolution, there is no need to send metric more often than that. 


Usage
-----

Very simple usage example, without exception handling.

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
