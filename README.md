python-librato
==============

[![Build Status](https://secure.travis-ci.org/librato/python-librato.png?branch=master)](http://travis-ci.org/librato/python-librato)

A Python wrapper for the Librato Metrics API.

## Installation

In your shell:

  ```$ easy_install librato-metrics```

  or

  ```$ pip install librato-metrics```

From your application or script:

  ```import librato```

## Authentication

  We first use our credentials to connect to the API. I am assuming you have
[a librato account for Metrics](https://metrics.librato.com/). Go to your
[account settings page](https://metrics.librato.com/account) and save your
username (email address) and token (long hexadecimal string).

```python
  api = librato.connect('email', 'token')
```

When creating your connection you may choose to provide a sanitization function.
This will be applied to any metric name you pass in. For example we provide a
sanitization function that will ensure your metrics are legal librato names.
This can be set as such

```python
  api = librato.connect('email', 'token', sanitizer=librato.sanitize_metric_name)
```

By default no sanitization is done.

## Basic Usage

To iterate over your metrics:

```python
  for m in api.list_metrics():
    print m.name
```

or use `list_metrics()` to iterate over all your metrics with
transparent pagination.

Let's now create a Metric:

```python
  api.submit("temperature", 10, description="temperature at home")
```

By default ```submit()``` will create a gauge metric. The metric will be
created automatically by the server if it does not exist

To create a counter metric:

```python
  api.submit("connections", 20, type="counter", description="server connections")
```

To iterate over your metric names:

```python
  for m in api.list_metrics():
      print "%s: %s" % (m.name, m.description)
```

To retrieve a specific metric:

```python
  gauge = api.get("temperature")
```

Delete a metric:

```python
  api.delete("temperature")
```

To retrieve a composite metric:

```python
  # Get average temperature across all cities for last 8 hours
  compose = 'mean(s("temperature", "*", {function: "mean", period: "3600"}))'
  import time
  start_time = int(time.time()) - 8 * 3600
  resp = api.get_composite(compose, start_time=start_time)
  resp['measurements'][0]['series']
  # [
  #   {u'measure_time': 1421744400, u'value': 41.23944444444444},
  #   {u'measure_time': 1421748000, u'value': 40.07611111111111},
  #   {u'measure_time': 1421751600, u'value': 38.77444444444445},
  #   {u'measure_time': 1421755200, u'value': 38.05833333333333},
  #   {u'measure_time': 1421758800, u'value': 37.983333333333334},
  #   {u'measure_time': 1421762400, u'value': 38.93333333333333},
  #   {u'measure_time': 1421766000, u'value': 40.556666666666665}
  # ]
```

To create a saved composite metric:

```python
  api.create_composite('humidity', 'sum(s("all.*", "*"))',
      description='a test composite')
```

Iterate over measurements:

```python
  metric = api.get("temperature", count=100, resolution=1)
  source = 'unassigned'
  for m in metric.measurements[source]:
    print "%s: %s" % (m['value'], m['measure_time'])
```

Notice a couple of things here. First, we are using the key `unassigned` since
we have not associated our measurements to any source. If we had specified a
source such as `sf` we could use it in the same fashion. Read more the
[API documentation](https://www.librato.com/docs/api/). In addition, notice how
we are passing the count and resolution parameters to make sure the API
returns measurements in its answer and not only the metric properties.
Read more about them [here](https://www.librato.com/docs/api/#retrieve-metric-by-name).

## Sending measurements in batch mode

Sending a measurement in a single HTTP request is inefficient. The overhead
both at protocol and backend level is very high. That's why we provide an
alternative method to submit your measurements. The idea is to send measurements
in batch mode. We push measurements that are stored and when we are
ready, they will be submitted in an efficient manner. Here is an example:

```python
api = librato.connect('email', 'token')
q   = api.new_queue()
q.add('temperature', 22.1, source='upstairs')
q.add('temperature', 23.1, source='dowstairs')
q.add('num_requests', 100, type='counter', source='server1')
q.add('num_requests', 102, type='counter', source='server2')
q.submit()
```

Queues can also be used as context managers. Once the context block is complete the queue
is submitted automatically. This is true even if an exception interrupts flow. In the
example below if ```potentially_dangerous_operation``` causes an exception the queue will
submit the first measurement as it was the only one successfully added.
If the operation succeeds both measurements will be submitted.

```python
api = librato.connect('email', 'token')
with api.new_queue() as q:
    q.add('temperature', 22.1, source='upstairs')
    potentially_dangerous_operation()
    q.add('num_requests', 100, type='counter', source='server1')
```

Queues by default will collect metrics until they are told to submit. You may create a queue
that autosubmits based on metric volume.

```python
api = librato.connect('email', 'token')
# Submit when the 400th metric is queued
q = api.new_queue(auto_submit_count=400)
```

## Updating Metric Attributes

You can update the information for a metric by using the `update` method,
for example:

```python
api = librato.connect('email', 'token')
for metric in api.list_metrics(name=" "):
  gauge = api.get(metric.name)
  attrs = gauge.attributes
  attrs['display_units_long'] = 'ms'
  api.update(metric.name, attributes=attrs)
```

## Multidimensional metric data streams

With multidimensional streams, it is possible to attach one or more user-defined properties (aka tags) to measurements
submitted to Librato. The user can then create advanced visualizations and alerts which rely on values of tags.
Tags are a generalization of the single-dimensional 'source' value which Librato has historically supported.

### Measurement-level tags

Multidimensional measurements can be submitted to Librato using the `submit_tagged()` method, which accepts an optional
 `tags` argument, which must be a dictionary with string keys and values. The following example shows how to submit
a measurement with `hostname` and `company` tags.

```
  api = librato.connect('email', 'token')
  api.submit_tagged("connections", 20, tags={'hostname': 'web-host-1', 'company': 'Librato'})
```

Multidimensional measurements can be submitted in batch mode using Queue's `add_tagged()` method, which also accepts an
optional `tags` dictionary argument.

```
  api = librato.connect('email', 'token')
  q   = api.new_queue()
  q.add_tagged("connections", 30, tags={'hostname': 'web-host-1', 'company': 'Librato'})
```

Note that multidimensional measurements must be submitted using `submit_tagged()` or `add_tagged()`, regardless
of whether or not a tag set has been specified. Any measurements submitted using `submit()` or `add()` will
be directed to the traditional (untagged) Librato backend. Also, it is possible to add tagged and untagged
measurements to a Queue instance, using `add_tagged()` and `add()`, respectively. Calling `submit()` will push
the measurements to the respective backends (multidimensional or traditional).

### Top-level tags

The above examples showed how to attach tags to individual measurements. It is also possible to attach top-level tags
to Connections and Queue instances, which effectively applies those tags to every measurement sent using the corresponding
instance. The top-level tags will be combined with, and superceded, by any measurement-specific tags.

The following example shows how to attach a `hostname` top-level tag to a Connection. The `connections` measurement will end
up with both `hostname` and a `company` tags.

```
  api = librato.connect('email', 'token', tags={'hostname': 'web-host-1'})
  api.submit_tagged("connections", 30, tags={'company': 'Librato'})
```

A Queue instance will inherit the top-level tags from the corresponding Connection object. In the following example,
the Queue instance will inherit `hostname` as a top-level tag from the Connecton instance. The `connections` measurement
will also end up with 'hostname' and 'company' tags.

```
  api = librato.connect('email', 'token', tags={'hostname': 'web-host-1'})
  q = api.new_queue()
  q.add_tagged("connections", 30, tags={'company': 'Librato'})
```

Top-level tag sets can be updated using `add_tags()` and replaced entirely using `set_tags()`, as shown below in the Connection
example below. The Queue class follows an identical pattern.

```
  api = librato.connect('email', 'token', tags={'hostname': 'web-host-1'})
  api.add_tags({'company': 'Librato'})        # Top-level tag set now has 'company' and 'hostname'
  api.set_tags({'hostname': 'web-host-2'})    # Top-level tag set only has 'hostname'
```

### Querying tagged measurements
Tagged measurements can be queried using the Connection `get_tagged()`. This method is much like `get()` but accepts a
`tags_search` parameter, that specifies a tag query string. Refer to the main developer documentation for additional details
on the search syntax. The following example shows a sample query that queries based hostname and company values.

```
  resp = api.get_tagged('connections', duration=60, tags_search="hostname=web-1 and company=Librato")
```

## Annotations

List Annotation all annotation streams:

```python
for stream in api.list_annotation_streams():
print("%s: %s" % (stream.name, stream.display_name))
```

View the metadata on a named annotation stream:

```python
stream = api.get_annotation_stream("api.pushes")
print stream
```

Retrieve all of the events inside a named annotation stream, by adding a
start_time parameter to the get_annotation_stream() call:

```python
stream=api.get_annotation_stream("api.pushes",start_time="1386050400")
for source in stream.events:
	print source
	events=stream.events[source]
	for event in events:
		print event['id']
		print event['title']
		print event['description']
```

Submit a new annotation to a named annotation stream (creates the stream if it
doesn't exist). Title is a required parameter, and all other parameters are optional

```python
api.post_annotation("testing",title="foobarbiz")

api.post_annotation("TravisCI",title="build %s"%travisBuildID,
                     source="SystemSource",
                     description="Application %s, Travis build %s"%(appName,travisBuildID),
                     links=[{'rel': 'travis', 'href': 'http://travisci.com/somebuild'}])
```

Delete a named annotation stream:

```python
api.delete_annotation_stream("testing")
```

## Spaces API
### List Spaces
```python
# List spaces
spaces = api.list_spaces()
```

### Create a Space
```python
# Create a new Space directly via API
space = api.create_space("space_name")
print("Created '%s'" % space.name)

# Create a new Space via the model, passing the connection
space = Space(api, 'Production')
space.save()
```

### Find a Space
```python
space = api.find_space('Production')
```

### Delete a Space
```python
space = api.create_space('Test')
api.delete_space(space.id)
# or
space.delete()
```

### Create a Chart
```python
# Create a Chart directly via API (defaults to line chart)
space = api.find_space('Production')
chart = api.create_chart(
    'cpu',
    space,
    streams=[{'metric': 'cpu.idle', 'source': '*'}]
)
```

```python
# Create line chart using the Space model
space = api.find_space('Production')

# You can actually create an empty chart (default to line)
chart = space.add_chart('cpu')

# Create a chart with all attributes
chart = space.add_chart(
    'memory',
    type='line',
    streams=[
      {'metric': 'memory.free', 'source': '*'},
      {'metric': 'memory.used', 'source': '*',
        'group_function': 'breakout', 'summary_function': 'average'}
    ],
    min=0,
    max=50,
    label='the y axis label',
    use_log_yaxis=True,
    related_space=1234
)
```

```python
# Shortcut to create a line chart with a single metric on it
chart = space.add_single_line_chart('my chart', 'my.metric', '*')
chart = space.add_single_line_chart('my chart', metric='my.metric', source='*')
```

```python
# Shortcut to create a stacked chart with a single metric on it
chart = space.add_single_stacked_chart('my chart', 'my.metric', '*')
```

```python
# Create a big number chart
bn = space.add_chart(
    'memory',
    type='bignumber',
    streams=[{'metric': 'my.metric', 'source': '*'}]
)
# Shortcut to add big number chart
bn = space.add_bignumber_chart('My Chart', 'my.metric', '*')
bn = space.add_bignumber_chart('My Chart', 'my.metric',
  source='*',
  group_function='sum',
  summary_function='sum',
  use_last_value=True
)
```

### Find a Chart
```python
# Takes either space_id or a space object
chart = api.get_chart(chart_id, space_id)
chart = api.get_chart(chart_id, space)
```

### Update a Chart
```python
chart = api.get_chart(chart_id, space_id)
chart.min = 0
chart.max = 50
chart.save()
```

### Rename a Chart
```python
chart = api.get_chart(chart_id, space_id)
# save() gets called automatically here
chart.rename('new chart name')
```

### Add new metrics to a Chart
```python
chart = space.charts()[-1]
chart.new_stream('foo', '*')
chart.new_stream(metric='foo', source='*')
chart.new_stream(composite='s("foo", "*")')
chart.save()
```

### Delete a Chart
```python
chart = api.get_chart(chart_id, space_id)
chart.delete()
```


## Alerts

List all alerts:

```python
for alert in api.list_alerts():
    print(alert.name)
```

Create alerts with an _above_ condition:
```python
alert = api.create_alert("name")
alert.add_condition_for('metric_name').above(1) # trigger immediately
alert.add_condition_for('metric_name').above(1).duration(60) # trigger after a set duration
alert.add_condition_for('metric_name').above(1, 'sum') # custom summary function
alert.save()
```

Create alerts with a _below_ condition:
```python
api.create_alert("name")
alert.add_condition_for('metric_name').below(1) # the same syntax as above conditions
alert.save()
```

Create alerts with an _absent_ condition:
```python
api.create_alert("name")
alert.add_condition_for('metric_name').stops_reporting_for(5) # duration in minutes of the threshold to trigger the alert
alert.save()
```

Add a description to an alert (default description is empty):
```python
api.create_alert("name", description='An alert description')
```

View all outbound services created by the user. The service ID is included in the response.
```python
for service in api.list_services():
    print(service._id, service.title, service.settings)
```

Add an outbound service to an alert:
```python
alert = api.create_alert("name")
alert.add_service("service ID")
alert.save()
```

To restrict the alert to a specific source (default is `*`):
```python
api.create_alert("name")
alert.add_condition_for('metric_name', source='source name')
alert.save()
```

## Client-side Aggregation

You can aggregate measurements before submission using the `Aggregator` class.  Optionally, specify a `measure_time` to submit that timestamp to the API.  You may also optionally specify a `period` to floor the timestamp to a particular interval.  If `period` is specified without a `measure_time`, the current timestamp will be used, and floored to `period`.  Specifying an optional `source` allows the aggregated measurement to report a source name.

Aggregator instances can be sent immediately by calling `submit()` or added to a `Queue` by calling `queue.add_aggregator()`.

```python
from librato.aggregator import Aggregator

api = librato.connect('email', 'token')

a = Aggregator(api)
a.add("foo", 42)
a.add("foo", 5)
# count=2, min=5, max=42, sum=47 (value calculated by API = mean = 23.5), source=unassigned
a.submit()

a = Aggregator(api, source='my.source', period=60)
a.add("foo", 42)
a.add("foo", 5)
# count=2, min=5, max=42, sum=47 (value calculated by API = mean = 23.5), source=my.source
# measure_time = <now> - (<now> % 60)
a.submit()

a = Aggregator(api, period=60, measure_time=1419302671)
a.add("foo", 42)
a.add("foo", 5)
# count=2, min=5, max=42, sum=47 (value calculated by API = mean = 23.5), source=unassigned
# measure_time = <now> - (<now> % 60) = 1419302640
a.submit()

a = Aggregator(api, measure_time=1419302671)
a.add("foo", 42)
a.add("foo", 5)
# count=2, min=5, max=42, sum=47 (value calculated by API = mean = 23.5), source=unassigned
# measure_time = 1419302671
a.submit()


# You can also add an Aggregator instance to a queue
q = librato.queue.Queue(api)
q.add_aggregator(a)
q.submit()
```

### Multidimensional Aggregator measurements

Tags can be associated with an Aggregator instance, much like Connection and Queue (see Multidimensional metric data streams
above), and aggregated using `add_tagged()`.

```
a = Aggregator(api, measure_time=1419302671, tags={'hostname': 'web-host-1'})
a.add_tagged('foo', 5)
```

Note that tagged measurements and untagged ones (aggregated using `add()`) are tracked separately by Aggregator, and submitted
to the respective metric backends.

```
a = Aggregator(api, measure_time=1419302671, tags={'hostname': 'web-host-1'})
a.add('foo', 5)           # Adds untagged measurement 'foo' to the aggregator
a.add_tagged('foo', 5)    # Adds a different tagged measurement called 'foo'
```

## Misc

### Timeouts

Timeouts are provided by the underlying http client. By default we timeout at 10 seconds. You can change
that by using `api.set_timeout(timeout)`.

## Contribution

Do you want to contribute? Do you need a new feature? Please open a
[ticket](https://github.com/librato/python-librato/issues).

## Contributors

The original version of `python-librato` was conceived/authored/released by Chris Moyer (AKA [@kopertop](https://github.com/kopertop)). He's
graciously handed over maintainership of the project to us and we're super-appreciative of his efforts.

## Copyright

Copyright (c) 2011-2016 [Librato Inc.](http://librato.com) See LICENSE for details.
