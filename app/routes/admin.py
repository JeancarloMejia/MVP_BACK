from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from app.models.database import db, Order, Product, Feedback
from app import socketio 

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/orders/active', methods=['GET'])
@jwt_required()
def get_active_orders():
    active_orders = Order.query.filter(
        Order.status.notin_(['FINALIZADO', 'CANCELADO'])
    ).order_by(Order.created_at.asc()).all()

    orders_list = []
    for order in active_orders:
        items_data = []
        for item in order.items:
            product = Product.query.get(item.product_id)
            items_data.append({
                'product_name': product.name if product else 'Producto Eliminado',
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'subtotal': float(item.subtotal)
            })

        orders_list.append({
            'id': order.id,
            'customer_name': order.customer_name,
            'customer_phone': order.customer_phone,
            'order_type': order.order_type,
            'delivery_address': order.delivery_address,
            'payment_type': order.payment_type,
            'delivery_fee': float(order.delivery_fee),
            'total_amount': float(order.total_amount),
            'status': order.status,
            'created_at': order.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'items': items_data
        })

    return jsonify({
        'status': 'success',
        'message': 'Pedidos activos cargados',
        'data': orders_list,
        'meta': {
            'total_orders': len(orders_list)
        }
    }), 200

@admin_bp.route('/orders/<order_id>/next-state', methods=['POST'])
@jwt_required()
def advance_order_state(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({
            'status': 'error',
            'message': 'Pedido no encontrado'
        }), 404

    current_status = order.status
    new_status = current_status

    if current_status == 'PENDIENTE':
        new_status = 'PREPARANDO'
    elif current_status == 'PREPARANDO':
        if order.order_type == 'DELIVERY':
            new_status = 'EN_CAMINO'
        else:
            new_status = 'LISTO_PARA_RECOJO'
    elif current_status in ['EN_CAMINO', 'LISTO_PARA_RECOJO']:
        new_status = 'FINALIZADO'
    elif current_status in ['FINALIZADO', 'CANCELADO']:
        return jsonify({
            'status': 'error',
            'message': 'El pedido ya está terminado, no puede avanzar más'
        }), 400

    if new_status != current_status:
        try:
            order.status = new_status
            db.session.commit()
            
            socketio.emit('actualizacion_estado', {
                'id': order.id,
                'order_id': order.id,
                'status': new_status
            })
            
            return jsonify({
                'status': 'success',
                'message': f'Pedido avanzado a {new_status}',
                'data': {
                    'order_id': order.id,
                    'new_status': new_status
                }
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Error al actualizar',
                'details': str(e)
            }), 500

    return jsonify({
        'status': 'success',
        'message': 'Sin cambios',
        'data': {
            'status': current_status
        }
    }), 200

@admin_bp.route('/orders/<order_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({
            'status': 'error',
            'message': 'Pedido no encontrado'
        }), 404

    if order.status in ['FINALIZADO', 'CANCELADO']:
        return jsonify({
            'status': 'error',
            'message': 'No se puede cancelar un pedido que ya está terminado o cancelado'
        }), 400

    try:
        order.status = 'CANCELADO'
        db.session.commit()
        
        socketio.emit('actualizacion_estado', {
            'id': order.id,
            'order_id': order.id,
            'status': 'CANCELADO'
        })
        
        return jsonify({
            'status': 'success',
            'message': 'Pedido cancelado con éxito',
            'data': {
                'order_id': order.id,
                'new_status': 'CANCELADO'
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Error al cancelar',
            'details': str(e)
        }), 500

@admin_bp.route('/feedbacks', methods=['GET'])
@jwt_required()
def get_feedbacks():
    feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).limit(50).all()
    feedbacks_list = [{
        'id': f.id,
        'customer_name': f.customer_name,
        'phone': f.phone,
        'message': f.message,
        'created_at': f.created_at.strftime("%Y-%m-%d %H:%M:%S")
    } for f in feedbacks]
    
    return jsonify({
        'status': 'success',
        'message': 'Comentarios cargados exitosamente',
        'data': feedbacks_list,
        'meta': {
            'total_feedbacks': len(feedbacks_list)
        }
    }), 200

@admin_bp.route('/revenue', methods=['GET'])
@jwt_required()
def get_revenue():
    try:
        total_revenue = db.session.query(func.sum(Order.total_amount)).filter(Order.status == 'FINALIZADO').scalar()
        total_revenue = float(total_revenue) if total_revenue else 0.00
        return jsonify({
            'status': 'success',
            'message': 'Ganancias calculadas exitosamente',
            'data': {
                'total_revenue': total_revenue
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Error al calcular las ganancias',
            'details': str(e)
        }), 500