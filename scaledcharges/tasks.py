import os
import stripe
import json
from celery import Celery
from celery.utils.log import get_task_logger
from flask_socketio import SocketIO, emit

CELERY_QUEUE = os.environ.get('BROKER_URL', 'redis://localhost:6379/0')
MESSAGE_QUEUE = os.environ.get('MESSAGE_QUEUE', 'redis://localhost:6379/1')

# Setup Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET')

# Setup Celery

celery_app = Celery('tasks', broker=CELERY_QUEUE)

# Configuration
MAX_RETRIES = 4
MAX_RETRY_TIME = 8

# Pull out logger
LOGGER = get_task_logger(__name__)


@celery_app.task(bind=True, default_retry_delay=2, retry_kwargs={'attempt': 1})
def create_charge(self, token, amount, idempotency_key, name, email):

    LOGGER.info('[t: {}][i: {}] Creating charge...'.format(
        token, idempotency_key
    ))

    result = {
        'success': False,
        'message': '',
        'data': {
            'charge_id': None,
            'amount': amount,
            'idempotency_key': idempotency_key,
            'name': name,
            'email': email,
        }
    }

    error_message = None
    try:

        # Create a charge
        ch = stripe.Charge.create(
            source=token,
            amount=amount,
            currency="usd",
            idempotency_key=idempotency_key,
            description="Charge for {0} <{1}>".format(name, email),
        )

        LOGGER.info('[t: {}][i: {}] Successfully created charge!'.format(
            token, idempotency_key
        ))

        result.update({
            'success': True,
            'message': 'Charge succeeded!'
        })
        result.get('data', {}).update({
            'charge_id': ch.id
        })

    except (stripe.error.APIConnectionError, stripe.error.RateLimitError) as e:

        LOGGER.warning('[t: {}][i: {}] Rate limited.  Falling back!'.format(
            token, idempotency_key
        ))

        # Rate limited
        if attempt < MAX_RETRIES:
            raise self.retry(exc=e, countdown=attempt, attempt=attempt + 1)

        result.update({
            'message': 'Maximum number of retries exceeded.  Failed.'
        })

    except stripe.error.CardError as e:

        # Card declined, probably
        result.update({'message': e.message})

    except Exception as e:

        # Any other error
        result.update({'message': str(e)})

    process_result.apply_async(args=(result))

    return True


@celery_app.task
def process_result(result):

    sio = SocketIO(message_queue=MESSAGE_QUEUE)
    idempotency_key = result.get('data', {}).get('idempotency_key')

    if idempotency_key:
        sio.emit(
            'charge_complete',
            {
                'data': json.dumps(result)
            },
            namespace='/' + idempotency_key
        )
        return True

    return False
