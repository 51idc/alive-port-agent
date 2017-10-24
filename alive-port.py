#!/usr/bin/env python
import time
import subprocess
import threading
import flask
import multiprocessing.pool

from service import metric_handler
from service import configHelper
from service.logHelper import LogHelper

CONFIG = configHelper.CONFIG
logger = LogHelper().logger


def generate_port_nc_metrics(ip, ports, endpoint, timeout, dc):
    metrics = []
    port_list = ports.split(';')
    for each_port in port_list:
        COMMAND = "nc -w %s %s %s && echo ok" % (timeout, ip, each_port)
        try:
            subp = subprocess.Popen(
                COMMAND,
                shell=True,
                stdout=subprocess.PIPE)
            output = subp.communicate()[0]
        except Exception:
            logger.error("unexpected error while execute cmd : %s" % COMMAND)
            continue

        if output.find("ok") > -1:
            m = metric_handler.gauge_metric(endpoint, "alive.port.port_alive", 1, port=each_port, DC=dc)
        else:
            m = metric_handler.gauge_metric(endpoint, "alive.port.port_alive", 0, port=each_port, DC=dc)
        m['step'] = CONFIG['step']
        metrics.append(m)
    m = metric_handler.gauge_metric(endpoint, "alive.port.alive", 1, DC=dc)
    m['step'] = CONFIG['step']
    metrics.append(m)
    return metrics


def alive(step):
    process_count = (multiprocessing.cpu_count() * 2 + 1) if (multiprocessing.cpu_count() * 2 + 1) < 11 else 10
    logger.info("multiprocess count is : %s" % process_count)
    DC = CONFIG["DC"]
    timeout = CONFIG["timeout"]
    targets = CONFIG['targets']
    while True:
        pool = multiprocessing.Pool(process_count)
        now = int(time.time())
        metrics = []
        result = []
        for key, val in targets.items():
            result.append(pool.apply_async(generate_port_nc_metrics, (val['ip'], val['ports'], key, timeout, DC)))
        pool.close()
        pool.join()

        for res in result:
            metrics.extend(res.get())
        metric_handler.push_metrics(metrics)

        dlt = time.time() - now
        logger.info("cycle finished . cost time : %s" % dlt)
        if dlt < step:
            time.sleep(step - dlt)


# flask app
app = flask.Flask(__name__)


@app.route("/add", methods=["POST"])
def add_alive_port():
    params = flask.request.get_json(force=True, silent=True)
    if not params:
        return flask.jsonify(status="error", msg="json parse error")

    logger.info("add_alive_port receive data : %s" % str(params))

    ip = params.get("ip", None)
    ports = params.get("ports", None)
    endpoint = params.get("endpoint", None)
    if not (ip and endpoint and ports):
        return flask.jsonify(status="error", msg="incomplete imfomation")

    targets = CONFIG["targets"]
    if endpoint in targets:
        return flask.jsonify(status="error", msg="duplicated endpoint")

    ip_ports = {
        "ip": ip,
        "ports": ports
    }
    targets[endpoint] = ip_ports
    logger.info("add alive_port success %s[%s %s]" % (endpoint, ip, ports))
    configHelper.write_config()
    return flask.jsonify(status="ok", msg="ok")


@app.route("/delete", methods=["POST"])
def delete_alive_port():
    params = flask.request.get_json(force=True, silent=True)
    if not params:
        return flask.jsonify(status="error", msg="json parse error")

    logger.info("delete_alive_port receive data : %s" % str(params))

    endpoint = params.get("endpoint", None)
    if not endpoint:
        return flask.jsonify(status="error", msg="incomplete information")

    targets = CONFIG["targets"]

    del targets[endpoint]
    logger.info("delete alive_port success %s" % endpoint)
    configHelper.write_config()
    return flask.jsonify(status="ok", msg="ok")


@app.route("/update", methods=["POST"])
def update_alive_port():
    params = flask.request.get_json(force=True, silent=True)
    if not params:
        return flask.jsonify(status="error", msg="json parse error")

    logger.info("update_alive_port receive data : %s" % str(params))

    ip = params.get("ip", None)
    ports = params.get("ports", None)
    endpoint = params.get("endpoint", None)
    if not (ip and endpoint and ports):
        return flask.jsonify(status="error", msg="incomplete imfomation")

    targets = CONFIG["targets"]
    if not endpoint in targets:
        return flask.jsonify(status="error", msg="no such endpoint")

    ip_ports = {
        "ip": ip,
        "ports": ports
    }
    targets[endpoint] = ip_ports
    logger.info("update alive_port success %s" % endpoint)
    configHelper.write_config()
    return flask.jsonify(status="ok", msg="ok")


@app.route("/list")
def list_alive_url():
    return flask.jsonify(CONFIG["targets"])


if __name__ == "__main__":
    t = threading.Thread(target=alive, args=(CONFIG['step'],))
    t.daemon = True
    t.start()

    app.run(host="0.0.0.0",
            port=CONFIG['http'],
            debug=CONFIG['debug'],
            use_reloader=False)
