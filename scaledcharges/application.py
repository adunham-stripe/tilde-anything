import os
import uuid
import random
from tasks import create_charge
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

MESSAGE_QUEUE = os.environ.get('MESSAGE_QUEUE', 'redis://localhost:6379/1')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'SECRETKEY!')
sio = SocketIO(app, message_queue=MESSAGE_QUEUE)


@app.route('/')
def index():
    context = {
        "uuid": str(uuid.uuid4()),              # build uuid for every user
        "amount": random.randint(50, 10000)     # random amount for the demo
    }
    return render_template('checkout.html', **context)


@app.route('/charge', methods=['POST'])
def charge():

    # Data
    # token, amount, idempotency_key, name, email

    data = request.get_json()
    create_charge.delay(**data)


@sio.on('connect')
def test_connect():
    print 'connected'
    emit('my response', {'data': 'Connected'})


@sio.on('disconnect')
def test_disconnect():
    print 'disconnected'


@sio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    send(username + ' has entered the room.', room=room)


@sio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    send(username + ' has left the room.', room=room)


@sio.on('message')
def test_message(message):
    print 'message', message
    emit('response', {'data': message})


if __name__ == '__main__':
    sio.run(app)
