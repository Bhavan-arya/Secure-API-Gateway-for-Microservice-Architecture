from flask import Flask, request, jsonify
from auth import require_auth
from rate_limiter import rate_limit
from telemetry import track_request, get_service_metrics
import requests
import os
import redis

app = Flask(__name__)

# Service URLs
SERVICE_URLS = {
    'user': 'http://user-service:5001',
    'order': 'http://order-service:5002',
    'product': 'http://product-service:5003'
}

# Connect to Redis
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')  # Redis container name in Docker
REDIS_PORT = os.getenv('REDIS_PORT', 6379)  # Default Redis port
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)

# Print environment variables for debugging
print("Environment Variables:")
print(f"JWT_SECRET_KEY: {os.getenv('JWT_SECRET_KEY')[:10]}...")  # Show first 10 chars
print(f"USER_SERVICE_URL: {os.getenv('USER_SERVICE_URL')}")
print(f"ORDER_SERVICE_URL: {os.getenv('ORDER_SERVICE_URL')}")
print(f"PRODUCT_SERVICE_URL: {os.getenv('PRODUCT_SERVICE_URL')}")
print(f"Redis Host: {REDIS_HOST}, Port: {REDIS_PORT}")

@app.route('/metrics', methods=['GET'])
@require_auth
def metrics():
    return jsonify({
        'user_service': get_service_metrics('user_service'),
        'order_service': get_service_metrics('order_service'),
        'product_service': get_service_metrics('product_service')
    })

@app.route('/users/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@track_request('user_service')
@rate_limit(max_requests=100, window_seconds=60)
def user_service(path):
    try:
        # Check Redis cache for data before forwarding the request
        cache_key = f"user_service:{path}"
        cached_response = redis_client.get(cache_key)
        if cached_response:
            return jsonify({"from_cache": True, "data": cached_response.decode('utf-8')}), 200

        # Forward request to the actual user service
        response = requests.request(
            method=request.method,
            url=f"{SERVICE_URLS['user']}/{path}",
            headers={key: value for key, value in request.headers if key != 'Host'},
            json=request.get_json() if request.is_json else None
        )
        
        # Cache response for future requests (optional)
        redis_client.set(cache_key, response.text, ex=60)  # Cache for 1 minute
        return response.json(), response.status_code
    except requests.RequestException as e:
        return jsonify({'error': 'User service unavailable', 'details': str(e)}), 503

@app.route('/orders/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@track_request('order_service')
@rate_limit(max_requests=100, window_seconds=60)
def order_service(path):
    try:
        # Check Redis cache for data before forwarding the request
        cache_key = f"order_service:{path}"
        cached_response = redis_client.get(cache_key)
        if cached_response:
            return jsonify({"from_cache": True, "data": cached_response.decode('utf-8')}), 200

        # Forward request to the actual order service
        response = requests.request(
            method=request.method,
            url=f"{SERVICE_URLS['order']}/{path}",
            headers={key: value for key, value in request.headers if key != 'Host'},
            json=request.get_json() if request.is_json else None
        )

        # Cache response for future requests (optional)
        redis_client.set(cache_key, response.text, ex=60)  # Cache for 1 minute
        return response.json(), response.status_code
    except requests.RequestException as e:
        return jsonify({'error': 'Order service unavailable', 'details': str(e)}), 503

@app.route('/products/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@track_request('product_service')
@rate_limit(max_requests=100, window_seconds=60)
def product_service(path):
    try:
        # Check Redis cache for data before forwarding the request
        cache_key = f"product_service:{path}"
        cached_response = redis_client.get(cache_key)
        if cached_response:
            return jsonify({"from_cache": True, "data": cached_response.decode('utf-8')}), 200

        # Forward request to the actual product service
        response = requests.request(
            method=request.method,
            url=f"{SERVICE_URLS['product']}/{path}",
            headers={key: value for key, value in request.headers if key != 'Host'},
            json=request.get_json() if request.is_json else None
        )

        # Cache response for future requests (optional)
        redis_client.set(cache_key, response.text, ex=60)  # Cache for 1 minute
        return response.json(), response.status_code
    except requests.RequestException as e:
        return jsonify({'error': 'Product service unavailable', 'details': str(e)}), 503

@app.route('/health', methods=['GET'])
def health_check():
    services_health = {}
    for service, url in SERVICE_URLS.items():
        try:
            response = requests.get(f"{url}/health")
            services_health[service] = 'healthy' if response.status_code == 200 else 'unhealthy'
        except requests.RequestException:
            services_health[service] = 'unavailable'
    
    return jsonify({
        'gateway': 'healthy',
        'services': services_health
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
