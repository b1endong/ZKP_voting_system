from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dataclasses import asdict
from typing import Optional, List
import json
import time

try:
    from hexbytes import HexBytes
except ImportError:
    # If hexbytes not available, create dummy class
    class HexBytes:
        pass

from chain_b import ChainB, BlockHeader, Block


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle bytes and HexBytes"""
    def default(self, obj):
        # Handle bytes
        if isinstance(obj, bytes):
            return '0x' + obj.hex()
        # Handle HexBytes (from web3)
        if hasattr(obj, 'hex'):
            return '0x' + obj.hex()
        return super().default(obj)


class ChainBRpcServer:
    """RPC Server for Chain B"""
    
    def __init__(self, chain_b: ChainB, port: int = 26657, admin_whitelist: List[str] = None):
        self.chain_b = chain_b
        self.port = port
        self.admin_whitelist = [addr.lower() for addr in admin_whitelist] if admin_whitelist else []
        self.app = Flask(__name__)
        self.app.json_encoder = CustomJSONEncoder  # Use custom encoder
        CORS(self.app, resources={r"/*": {"origins": "*"}})
        
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'ok',
                'chainId': self.chain_b.chain_id,
                'blockHeight': self.chain_b.height
            })

        @self.app.route('/rpc', methods=['POST'])
        def rpc():
            """JSON-RPC 2.0 endpoint"""
            try:
                data = request.get_json()
                jsonrpc = data.get('jsonrpc')
                method = data.get('method')
                params = data.get('params', [])
                rpc_id = data.get('id')
                
                if jsonrpc != '2.0':
                    return jsonify({
                        'jsonrpc': '2.0',
                        'error': {
                            'code': -32600,
                            'message': 'Invalid Request - must use JSON-RPC 2.0'
                        },
                        'id': rpc_id
                    }), 400

                result = self._handle_rpc_method(method, params)

                # Convert result to JSON string manually
                result_json_str = json.dumps({
                    'jsonrpc': '2.0',
                    'result': result,
                    'id': rpc_id
                }, cls=CustomJSONEncoder)

                return Response(result_json_str, mimetype='application/json')

            except Exception as e:
                return jsonify({
                    'jsonrpc': '2.0',
                    'error': {
                        'code': -32603,
                        'message': str(e)
                    },
                    'id': data.get('id') if 'data' in locals() else None
                }), 500

        @self.app.route('/api/chain-info', methods=['GET'])
        def chain_info():
            return jsonify(self.chain_b.get_chain_info())

        @self.app.route('/api/block/<int:height>', methods=['GET'])
        def get_block(height):
            try:
                block = self.chain_b.get_block(height)
                return jsonify(self._serialize_block(block))
            except ValueError as e:
                return jsonify({'error': str(e)}), 404

        @self.app.route('/api/latest-block', methods=['GET'])
        def latest_block():
            try:
                block = self.chain_b.get_latest_block()
                if block:
                    return jsonify(self._serialize_block(block))
                return jsonify({'error': 'No blocks yet'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # ==================== VOTER CLIENT ENDPOINTS ====================
        
        @self.app.route('/get_merkle_root', methods=['GET'])
        def get_merkle_root():
            """Get merkle root and tree metadata (public info only)"""
            try:
                root_val = self.chain_b.merkle_tree.root
                if isinstance(root_val, bytes):
                    root_val = '0x' + root_val.hex()
                
                return jsonify({
                    'merkle_root': root_val,
                    'merkle_depth': self.chain_b.merkle_tree.depth,
                    'total_voters': len(self.chain_b.users)
                })

            except Exception as e:
                import traceback
                traceback.print_exc()
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/get_merkle_proof', methods=['POST'])
        def get_merkle_proof():
            """Calculate merkle proof for a specific commitment (server-side)"""
            try:
                data = request.get_json()
                commitment = data.get('commitment')
                
                if not commitment:
                    return jsonify({'error': 'Missing commitment'}), 400
                
                # Parse commitment (can be decimal string or hex string)
                if isinstance(commitment, str):
                    if commitment.startswith('0x') or commitment.startswith('0X'):
                        commitment_int = int(commitment, 16)
                    else:
                        # Decimal string
                        commitment_int = int(commitment)
                elif isinstance(commitment, int):
                    commitment_int = commitment
                else:
                    return jsonify({'error': 'Invalid commitment format'}), 400
                
                # Find user by matching commitment with merkle tree leaves
                user_id = None
                target_leaf = None
                
                # Debug: Log what client sent
                print(f"\n🔍 Client commitment: {commitment_int}")
                print(f"📋 Checking merkle tree with {len(self.chain_b.merkle_tree.leaves)} leaves...")
                
                # Search in merkle tree leaves (which are already hashed commitments)
                if self.chain_b.merkle_tree and self.chain_b.merkle_tree.leaves:
                    for i, leaf in enumerate(self.chain_b.merkle_tree.leaves):
                        # Get corresponding user_id from user_list
                        if i < len(self.chain_b.user_list):
                            uid = self.chain_b.user_list[i]
                            
                            # Debug: Show each comparison
                            leaf_hex = '0x' + format(leaf, '064x')
                            print(f"   Leaf[{i}] ({uid}): {leaf_hex}")
                            
                            if leaf == commitment_int:
                                user_id = uid
                                target_leaf = hex(leaf)
                                print(f"   ✅ MATCH! Found user: {uid} at index {i}")
                                break
                else:
                    return jsonify({'error': 'Merkle tree not initialized. Please produce a block first.'}), 500
                
                if not user_id:
                    print(f"   ❌ No match found!")
                    return jsonify({
                        'error': 'Commitment not found in voter registry',
                        'debug': {
                            'client_commitment': str(commitment_int),
                            'total_leaves': len(self.chain_b.merkle_tree.leaves) if self.chain_b.merkle_tree else 0,
                            'hint': 'Check if secret is correct or if merkle tree is updated'
                        }
                    }), 404
                
                # Get merkle path from Chain B (it already has the logic)
                path_data = self.chain_b.get_path(user_id)
                
                return jsonify({
                    'merkle_root': hex(path_data['merkleRoot']),
                    'merkle_depth': self.chain_b.merkle_tree.fixed_depth,
                    'leaf_index': path_data['leafIndex'],
                    'path_elements': [hex(elem) for elem in path_data['pathElements']],
                    'path_indices': path_data['pathIndices']
                })

            except Exception as e:
                import traceback
                traceback.print_exc()
                return jsonify({'error': str(e)}), 500

        @self.app.route('/calculate_commitment', methods=['POST'])
        def calculate_commitment():
            """Calculate commitment from secret (helper for Admin Portal)"""
            try:
                data = request.get_json()
                secret = data.get('secret')
                
                if not secret:
                    return jsonify({'error': 'Missing secret'}), 400
                
                from circomlibpy.poseidon import PoseidonHash
                poseidon = PoseidonHash()
                commitment = poseidon.hash(1, [int(secret)])
                
                return jsonify({
                    'commitment': hex(commitment)
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # ==================== ADMIN PORTAL ENDPOINTS ====================
        
        @self.app.route('/check_admin', methods=['POST'])
        def check_admin():
            """Check if address is admin/validator"""
            try:
                data = request.get_json()
                address = data.get('address', '').lower()
                
                # Check whitelist first (for demo/testing with MetaMask)
                if address in self.admin_whitelist:
                    return jsonify({
                        'is_admin': True,
                        'address': address,
                        'source': 'whitelist'
                    })
                
                # Check if address is in validator set
                validator_addresses = [v.lower() for v in self.chain_b.get_validator_addresses()]
                
                is_admin = address in validator_addresses
                
                return jsonify({
                    'is_admin': is_admin,
                    'address': address,
                    'source': 'validator' if is_admin else 'none'
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/submit_transaction', methods=['POST'])
        def submit_transaction():
            """Submit ADD_VOTER or REMOVE_VOTER transaction"""
            try:
                data = request.get_json()
                tx = data.get('transaction')
                signature = data.get('signature')
                from_address = data.get('from')
                
                if not all([tx, signature, from_address]):
                    return jsonify({'error': 'Missing required fields'}), 400
                
                tx_type = tx.get('type')
                commitment = tx.get('commitment')
                
                if tx_type == 'ADD_VOTER':
                    # Check whitelist or validator permission
                    if from_address.lower() not in self.admin_whitelist:
                        validator_addresses = [v.lower() for v in self.chain_b.get_validator_addresses()]
                        if from_address.lower() not in validator_addresses:
                            return jsonify({'error': 'Unauthorized: not a validator'}), 403
                    
                    # Extract user data from transaction
                    user_id = tx.get('userId', commitment[:10])
                    commitment_int = int(commitment, 16) if isinstance(commitment, str) else commitment
                    
                    # Find proposer index
                    proposer_index = 0
                    for i, addr in enumerate(self.chain_b.get_validator_addresses()):
                        if addr.lower() == from_address.lower():
                            proposer_index = i
                            break
                    
                    # Create proposal
                    proposal_id = self.chain_b.propose_add_user(user_id, commitment_int, proposer_index)
                    
                    # Auto-approve from other validators (simplified for demo)
                    # In production, this would be a separate voting process
                    for i in range(self.chain_b.num_validators):
                        addr = self.chain_b.validator_accounts[i].address
                        if addr.lower() != from_address.lower():
                            self.chain_b.vote_proposal(proposal_id, i)
                    
                    return jsonify({
                        'success': True,
                        'tx_hash': f'0x{proposal_id[:16]}',
                        'proposal_id': proposal_id,
                        'message': 'Voter added successfully'
                    })
                
                elif tx_type == 'REMOVE_VOTER':
                    # Check whitelist or validator permission
                    if from_address.lower() not in self.admin_whitelist:
                        validator_addresses = [v.lower() for v in self.chain_b.get_validator_addresses()]
                        if from_address.lower() not in validator_addresses:
                            return jsonify({'error': 'Unauthorized: not a validator'}), 403
                    
                    # Find proposer index
                    proposer_index = 0
                    for i, addr in enumerate(self.chain_b.get_validator_addresses()):
                        if addr.lower() == from_address.lower():
                            proposer_index = i
                            break
                    
                    user_id = tx.get('userId', commitment[:10])
                    proposal_id = self.chain_b.propose_remove_user(user_id, proposer_index)
                    
                    # Auto-approve
                    for i in range(self.chain_b.num_validators):
                        addr = self.chain_b.validator_accounts[i].address
                        if addr.lower() != from_address.lower():
                            self.chain_b.vote_proposal(proposal_id, i)
                    
                    return jsonify({
                        'success': True,
                        'tx_hash': f'0x{proposal_id[:16]}',
                        'proposal_id': proposal_id,
                        'message': 'Voter removed successfully'
                    })
                
                else:
                    return jsonify({'error': f'Unknown transaction type: {tx_type}'}), 400
                    
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/get_voters', methods=['GET'])
        def get_voters():
            """Get list of all voters"""
            try:
                voters = []
                for user_id, user_data in self.chain_b.users.items():
                    voters.append({
                        'commitment': user_id,
                        'name': user_id,
                        'added_at': int(time.time() * 1000)  # Mock timestamp
                    })
                
                return jsonify({
                    'voters': voters,
                    'count': len(voters)
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/get_status', methods=['GET'])
        def get_status():
            """Get Chain B status for Admin Portal"""
            try:
                latest_block = self.chain_b.get_latest_block()
                
                return jsonify({
                    'latest_block': latest_block.height if latest_block else 0,
                    'merkle_root': hex(self.chain_b.merkle_root),
                    'validator_count': self.chain_b.num_validators,
                    'voter_count': len(self.chain_b.users),
                    'chain_id': self.chain_b.chain_id
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/produce_block', methods=['POST'])
        def produce_block():
            """Produce new block (Admin only)"""
            try:
                data = request.get_json()
                from_address = data.get('from', '').lower()
                
                # Check whitelist or validator permission
                if from_address not in self.admin_whitelist:
                    validator_addresses = [v.lower() for v in self.chain_b.get_validator_addresses()]
                    if from_address not in validator_addresses:
                        return jsonify({'error': 'Unauthorized: not a validator'}), 403
                
                # Produce block
                block = self.chain_b.produce_block()
                
                if block:
                    return jsonify({
                        'success': True,
                        'block_height': block.height,
                        'merkle_root': hex(block.stateRoot),
                        'timestamp': block.timestamp,
                        'signatures': len(block.signatures),
                        'message': f'Block #{block.height} created successfully'
                    })
                else:
                    return jsonify({'error': 'Failed to produce block'}), 500
                    
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    def _handle_rpc_method(self, method: str, params: list):
        """Handle RPC method calls"""
        # Format params for display
        display_params = [
            p[:10] + '...' if isinstance(p, str) and len(p) > 20 else p
            for p in params[:2]
        ]
        if len(params) > 2:
            display_params.append('...')
        
        print(f"\n🔍 RPC Call: {method}({', '.join(map(str, display_params))})")

        if method in ['chainb_getPath', 'getPath']:
            user_id = params[0]
            path_data = self.chain_b.get_path(user_id)
            print(f"   ✓ Returned path with {len(path_data['pathElements'])} siblings")
            return path_data

        elif method in ['chainb_getBlockHeader', 'getBlockHeader']:
            height = params[0]
            result = self.chain_b.get_block(height)
            print(f"   ✓ Returned block header #{height}")
            return self._serialize_block(result)

        elif method in ['chainb_getLatestBlock', 'getLatestBlock']:
            result = self.chain_b.get_latest_block()
            if result:
                print(f"   ✓ Returned latest block #{result.height}")
                return self._serialize_block(result)
            return None

        elif method in ['chainb_getChainInfo', 'getChainInfo']:
            result = self.chain_b.get_info()
            print(f"   ✓ Returned chain info")
            return result

        elif method in ['chainb_hasVoter', 'hasVoter']:
            user_id = params[0]
            result = user_id in self.chain_b.users
            print(f"   ✓ Voter exists: {result}")
            return result

        elif method in ['chainb_getValidators', 'getValidators']:
            result = self.chain_b.get_validator_addresses()
            print(f"   ✓ Returned {len(result)} validators")
            return result

        elif method in ['chainb_getMerkleRoot', 'getMerkleRoot']:
            block_height = params[0] if params else None
            if block_height:
                block = self.chain_b.get_block(block_height)
                return block.stateRoot
            return self.chain_b.merkle_root

        else:
            raise ValueError(f"Method not found: {method}")

    def _serialize_block(self, block: Block) -> dict:
        """Serialize Block to JSON-safe dict"""
        result = {
            'height': block.height,
            'stateRoot': block.stateRoot,
            'timestamp': block.timestamp,
            'parentHash': block.parentHash,
            'blockHash': block.blockHash,
            'signatures': [],
            'valid_signature_count': block.valid_signature_count,
            'proposer_index': block.proposer_index
        }
        
        # Convert bytes/HexBytes signatures to hex strings
        for sig in block.signatures:
            if isinstance(sig, bytes):
                result['signatures'].append('0x' + sig.hex())
            elif isinstance(sig, HexBytes):
                result['signatures'].append('0x' + sig.hex())
            else:
                result['signatures'].append(str(sig))
        
        return result

    def start(self):
        """Start the RPC server"""
        print(f"\n🌐 Chain B RPC Server started")
        print(f"   Listening on: http://localhost:{self.port}")
        print(f"   Endpoints:")
        print(f"      JSON-RPC 2.0:")
        print(f"         POST http://localhost:{self.port}/rpc")
        print(f"      REST API:")
        print(f"         GET  http://localhost:{self.port}/health")
        print(f"         GET  http://localhost:{self.port}/api/chain-info")
        print(f"         GET  http://localhost:{self.port}/api/block/<height>")
        print(f"         GET  http://localhost:{self.port}/api/latest-block")
        print(f"      Voter Client API:")
        print(f"         GET  http://localhost:{self.port}/get_merkle_root")
        print(f"         POST http://localhost:{self.port}/get_merkle_proof")
        print(f"         POST http://localhost:{self.port}/calculate_commitment")
        print(f"      Admin Portal API:")
        print(f"         POST http://localhost:{self.port}/check_admin")
        print(f"         POST http://localhost:{self.port}/submit_transaction")
        print(f"         POST http://localhost:{self.port}/produce_block")
        print(f"         GET  http://localhost:{self.port}/get_voters")
        print(f"         GET  http://localhost:{self.port}/get_status")
        
        self.app.run(host='0.0.0.0', port=self.port, debug=False)


class ChainBRpcClient:
    """Client helper for making RPC calls"""
    
    def __init__(self, rpc_url: str = 'http://localhost:26657'):
        self.rpc_url = rpc_url
        self.request_id = 0

    def call(self, method: str, params: list = None):
        """Make an RPC call"""
        import requests
        
        if params is None:
            params = []
        
        self.request_id += 1
        
        response = requests.post(
            f"{self.rpc_url}/rpc",
            json={
                'jsonrpc': '2.0',
                'method': method,
                'params': params,
                'id': self.request_id
            },
            headers={'Content-Type': 'application/json'}
        )
        
        data = response.json()
        
        if 'error' in data:
            raise Exception(f"RPC Error: {data['error']['message']}")
        
        return data['result']

    def get_path(self, commitment: str, block_height: Optional[int] = None):
        return self.call('chainb_getPath', [commitment, block_height])

    def get_path(self, user_id: str):
        return self.call('chainb_getPath', [user_id])

    def get_block(self, height: int):
        return self.call('chainb_getBlockHeader', [height])

    def get_latest_block(self):
        return self.call('chainb_getLatestBlock', [])

    def get_info(self):
        return self.call('chainb_getChainInfo', [])

    def has_voter(self, user_id: str):
        return self.call('chainb_hasVoter', [user_id])

    def get_validator_addresses(self):
        return self.call('chainb_getValidators', [])

    def get_merkle_root(self, block_height: Optional[int] = None):
        return self.call('chainb_getMerkleRoot', [block_height])


def main():
    """Demo"""
    import time
    import threading
    
    print('=' * 60)
    print('Chain B RPC Server Demo')
    print('=' * 60)
    
    # Create Chain B
    chain_b = ChainB(num_validators=5, threshold=3, merkle_depth=2)
    
    # Add voters via consensus
    print('\n📋 Setting up Chain B with consensus...')
    
    # Admin whitelist for demo (MetaMask addresses that can act as admin)
    admin_whitelist = [
        "0xD55B67EaF6B7C11C813aaa077467a889B58c17A4",  # Your MetaMask address
    ]
    
    # Start RPC server in a separate thread
    rpc_server = ChainBRpcServer(chain_b, 5000, admin_whitelist)
    
    def run_server():
        rpc_server.start()
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    # Test RPC client
    print('\n📋 Testing RPC Client...')
    client = ChainBRpcClient('http://localhost:5000')
    
    print('\n✅ RPC Server is running. Press Ctrl+C to stop.')
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n\nShutting down...')


if __name__ == '__main__':
    main()
