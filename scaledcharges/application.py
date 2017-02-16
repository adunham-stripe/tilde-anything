import os
import uuid
import random
from tasks import create_charge
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, send, join_room, leave_room

# Configuration variables
MESSAGE_QUEUE = os.environ.get('MESSAGE_QUEUE', 'redis://localhost:6379/1')

# Environmental variables
SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret-key')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')


app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
sio = SocketIO(app, message_queue=MESSAGE_QUEUE)


@app.route('/')
def index():
    context = {
        "uuid": str(uuid.uuid4()),              # build uuid for every user
        "amount": random.randint(50, 10000),    # random amount for the demo
        "STRIPE_PUBLISHABLE_KEY": STRIPE_PUBLISHABLE_KEY
    }
    return render_template('checkout.html', **context)


@app.route('/charge', methods=['POST'])
def charge():

    data = request.form

    print 'CREATE A CHARGE'
    print '-' * 80
    print data
    print '-' * 80

    # Data - token, amount, idempotency_key, name, email

    create_charge.delay(**dict([(k, data.get(k)) for k in data.keys()]))

    return "OK"


@app.route('/notify', methods=['POST'])
def notify():

    data = request.get_json()
    idempotency_key = data.get('data', {}).get('idempotency_key')

    print 'CREATE NOTIFICATION'
    print '-' * 80
    print data
    print idempotency_key
    print '-' * 80

    sio.emit('res', data, room=idempotency_key)
    return "OK"

@sio.on('connect')
def test_connect():
    emit('message', {'data': 'Client has connected.'})


@sio.on('disconnect')
def test_disconnect():
    pass


@sio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    emit('message', {'data': 'Client has entered the room.'}, room=room)


@sio.on('leave')
def on_leave(data):
    room = data['room']
    emit('message', {'data': 'Client has left the room.'}, room=room)
    leave_room(room)


@sio.on('message')
def message(data):
    print data


if __name__ == '__main__':
    sio.run(app)
