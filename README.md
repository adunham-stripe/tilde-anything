# Flash Sales w/ Websockets

This is a demonstration of how to build a payments that can process enormous customer volumes reliably with Stripe.  The charges are processed asynchronously, using a worker queue powered by "Celery".  The results of the charge requests are transmitted over a websocket (unique to each customer), so there is no polling involved.

## Installation

### Step #1: Install External Requirements

- _Redis_ - `brew install redis`
- _Socket.io_ - `npm install socketio`

### Step #2: Install Python Requirements

`pip install -r requirements.txt`

## Running in Console

Ideally, this will be deployable to something like Heroku or Dokku; but I've not gotten that far yet-- so this will have to do for now.

Make sure you have Redis running (it probably already is).

### Step #1: Turn on the Celery Worker Queue

`STRIPE_SECRET_KEY=sk_test_xxx celery -A scaledcharges.tasks worker --loglevel=info -E`

### Step #2: Turn on the Web Server

`STRIPE_SECRET_KEY=sk_test_xxx STRIPE_PUBLISHABLE_KEY=pk_test_xxx python run.py`

## How it works

![Flash Sales w/ Websockets](https://i.leetfil.es/c8458b5f)

### Steps

  1. Customer requests payment (index) page (`/`) and is assigned a UUID by the Flask server.
  2. Customer submits payment information via Stripe.js to `/v1/tokens` and receives a payment token (eg. `tok_xxx`).
  3. Customer subscribes to a unique websocket room for the UUID.
  4. Customer passes the token (eg. `tok_xxx`) and UUID (among other things) to the `/charges`-endpoint.  (Everything after this point is asynchronous -- so a "payment pending"-spinner is created.)
  5. An asynchronous task, `create_charge` is spawned in Celery.
  6. The asynchronous task creates a charge (eg. `ch_xxx`) in Stripe, by sending a request to the `/v1/charges`-endpoint.
  7. The asynchronous task spawns a sub-task to process the newly created charge (eg. `ch_xxx`) called `process_response`.
  8. The asynchronous sub-task sends a request to the `/notify`-endpoint with the charge (eg. `ch_xxx`).
  9. The `/notify` endpoint notifies the unique websocket room with the results of the charge attempt which are intercepted by the customer's subscription to that websocket.
