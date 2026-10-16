from decimal import Decimal
from flask import Blueprint, request, jsonify
from app.models.database import db, Order, OrderItem, Product, Feedback
from app.utils.helpers import generate_tracking_id
from app import socketio 

public_bp = Blueprint('public', __name__)

@public_bp.route('/products', methods=['GET'])
def get_products():
    products = Product.query.filter_by(is_active=True).all()
    products_list = [
        {
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'price': float(p.price),
            'image': p.image
        } for p in products
    ]
    return jsonify({
        'status': 'success',
        'message': 'Menú cargado exitosamente',
        'data': products_list,
        'meta': {
            'total_items': len(products_list)
        }
    }), 200

@public_bp.route('/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    if not data or 'items' not in data or len(data['items']) == 0:
        return jsonify({
            'status': 'error',
            'message': 'El carrito está vacío'
        }), 400

    order_type = data.get('order_type')
    if order_type not in ['DELIVERY', 'RECOJO_TIENDA']:
        return jsonify({
            'status': 'error',
            'message': 'Tipo de orden inválido'
        }), 400

    tracking_id = generate_tracking_id()
    while Order.query.get(tracking_id):
        tracking_id = generate_tracking_id()

    total_amount = Decimal('0.00')
    order_items_to_insert = []
    
    for item in data['items']:
        product = Product.query.get(item['product_id'])
        if not product or not product.is_active:
            return jsonify({
                'status': 'error',
                'message': f"Producto ID {item['product_id']} no disponible"
            }), 400
        
        quantity = int(item['quantity'])
        unit_price = product.price
        subtotal = unit_price * quantity
        total_amount += subtotal
        
        order_items_to_insert.append(
            OrderItem(
                order_id=tracking_id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=subtotal
            )
        )

    delivery_fee = Decimal('5.00') if order_type == 'DELIVERY' else Decimal('0.00')
    total_amount += delivery_fee

    items_data_socket = []
    for oi in order_items_to_insert:
        prod = Product.query.get(oi.product_id)
        items_data_socket.append({
            'product_name': prod.name if prod else 'Producto',
            'quantity': oi.quantity,
            'unit_price': float(oi.unit_price),
            'subtotal': float(oi.subtotal)
        })

    new_order = Order(
        id=tracking_id,
        customer_name=data['customer_name'],
        customer_phone=data['customer_phone'],
        order_type=order_type,
        delivery_address=data.get('delivery_address', ''),
        payment_type=data['payment_type'],
        delivery_fee=delivery_fee,
        total_amount=total_amount,
        status='PENDIENTE'
    )

    try:
        db.session.add(new_order)
        db.session.flush()
        db.session.bulk_save_objects(order_items_to_insert)
        db.session.commit()

        socketio.emit('nuevo_pedido', {
            'id': tracking_id,
            'customer_name': new_order.customer_name,
            'customer_phone': new_order.customer_phone,
            'order_type': new_order.order_type,
            'delivery_address': new_order.delivery_address,
            'payment_type': new_order.payment_type,
            'delivery_fee': float(new_order.delivery_fee),
            'total_amount': float(new_order.total_amount),
            'status': new_order.status,
            'created_at': new_order.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'items': items_data_socket
        }, to='admin_room')

        return jsonify({
            'status': 'success',
            'message': 'Pedido creado con éxito',
            'data': {
                'tracking_id': tracking_id
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Error al procesar el pedido',
            'details': str(e)
        }), 500

@public_bp.route('/tracking/<order_id>', methods=['GET'])
def get_tracking(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({
            'status': 'error',
            'message': 'Pedido no encontrado'
        }), 404

    return jsonify({
        'status': 'success',
        'message': 'Tracking obtenido correctamente',
        'data': {
            'id': order.id,
            'customer_name': order.customer_name,
            'order_type': order.order_type,
            'status': order.status,
            'total_amount': float(order.total_amount),
            'created_at': order.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
    }), 200

@public_bp.route('/feedbacks', methods=['POST'])
def submit_feedback():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({
            'status': 'error',
            'message': 'El mensaje es obligatorio'
        }), 400

    new_feedback = Feedback(
        customer_name=data.get('customer_name', 'Anónimo'),
        phone=data.get('phone', ''),
        message=data['message']
    )

    try:
        db.session.add(new_feedback)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Comentario enviado con éxito',
            'data': None
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Error al guardar el comentario',
            'details': str(e)
        }), 500