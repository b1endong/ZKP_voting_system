"""
Run Relayer to monitor Chain B RPC and sync to Sepolia LightClient

Usage:
    python run_relayer.py

Flow:
1. Connect to Chain B RPC (http://localhost:5000)
2. Connect to Sepolia LightClient contract
3. Poll Chain B every 5 seconds for new blocks
4. When new block found → Submit header to LightClient
"""

from email import header
import time
import asyncio
from sympy import false, true
from web3 import Web3
from eth_account import Account
import requests
import json
import os
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configuration
CHAIN_B_RPC = "http://localhost:5000"
SEPOLIA_RPC = os.getenv("SEPOLIA_RPC_URL", "https://sepolia.infura.io/v3/YOUR_KEY")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
LIGHT_CLIENT_ADDRESS = "0x191CAa18062a9f9D41314dbbe97A94850bc4b031"  # Update with your deployed address

# LightClient ABI (minimal)
LIGHT_CLIENT_ABI = [{"inputs":[{"internalType":"address[]","name":"_owners","type":"address[]"},{"internalType":"uint256","name":"_threshold","type":"uint256"},{"internalType":"bytes32","name":"_genesisMerkleRoot","type":"bytes32"}],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[{"internalType":"address","name":"signer","type":"address"}],"name":"DuplicateSignature","type":"error"},{"inputs":[],"name":"InvalidBlockHeight","type":"error"},{"inputs":[],"name":"InvalidParentHash","type":"error"},{"inputs":[{"internalType":"uint256","name":"index","type":"uint256"}],"name":"InvalidSignature","type":"error"},{"inputs":[],"name":"InvalidThreshold","type":"error"},{"inputs":[],"name":"InvalidTimestamp","type":"error"},{"inputs":[{"internalType":"address","name":"signer","type":"address"}],"name":"NotAnOwner","type":"error"},{"inputs":[{"internalType":"uint256","name":"provided","type":"uint256"},{"internalType":"uint256","name":"required","type":"uint256"}],"name":"NotEnoughSignatures","type":"error"},{"inputs":[],"name":"ZeroAddress","type":"error"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"blockHeight","type":"uint256"},{"indexed":true,"internalType":"bytes32","name":"merkleRoot","type":"bytes32"},{"indexed":false,"internalType":"bytes32","name":"blockHash","type":"bytes32"},{"indexed":false,"internalType":"uint256","name":"validSignatures","type":"uint256"},{"indexed":true,"internalType":"address","name":"relayer","type":"address"}],"name":"HeaderSubmitted","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"}],"name":"OwnerAdded","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"resetToHeight","type":"uint256"},{"indexed":false,"internalType":"bytes32","name":"genesisRoot","type":"bytes32"}],"name":"StateReset","type":"event"},{"inputs":[{"internalType":"address","name":"addr","type":"address"}],"name":"checkIsOwner","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getConfig","outputs":[{"internalType":"uint256","name":"_threshold","type":"uint256"},{"internalType":"uint256","name":"_ownerCount","type":"uint256"},{"internalType":"address[]","name":"_owners","type":"address[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"blockHeight","type":"uint256"}],"name":"getHeader","outputs":[{"components":[{"internalType":"uint256","name":"blockHeight","type":"uint256"},{"internalType":"bytes32","name":"merkleRoot","type":"bytes32"},{"internalType":"uint256","name":"timestamp","type":"uint256"},{"internalType":"bytes32","name":"parentHash","type":"bytes32"},{"internalType":"bytes32","name":"blockHash","type":"bytes32"}],"internalType":"struct Updater.BlockHeader","name":"","type":"tuple"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getLatestRoot","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getOwners","outputs":[{"internalType":"address[]","name":"","type":"address[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"blockHeight","type":"uint256"}],"name":"getRootAtHeight","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"isOwner","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"blockHeight","type":"uint256"},{"internalType":"bytes32","name":"merkleRoot","type":"bytes32"}],"name":"isValidRoot","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"latestBlockHeight","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"latestValidRoot","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"ownerCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"owners","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"resetState","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"components":[{"internalType":"uint256","name":"blockHeight","type":"uint256"},{"internalType":"bytes32","name":"merkleRoot","type":"bytes32"},{"internalType":"uint256","name":"timestamp","type":"uint256"},{"internalType":"bytes32","name":"parentHash","type":"bytes32"},{"internalType":"bytes32","name":"blockHash","type":"bytes32"}],"internalType":"struct Updater.BlockHeader","name":"_header","type":"tuple"},{"internalType":"bytes[]","name":"signatures","type":"bytes[]"}],"name":"submitHeader","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"threshold","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"validRoots","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"verifiedHeaders","outputs":[{"internalType":"uint256","name":"blockHeight","type":"uint256"},{"internalType":"bytes32","name":"merkleRoot","type":"bytes32"},{"internalType":"uint256","name":"timestamp","type":"uint256"},{"internalType":"bytes32","name":"parentHash","type":"bytes32"},{"internalType":"bytes32","name":"blockHash","type":"bytes32"}],"stateMutability":"view","type":"function"}]

class ChainBClient:
    """Client to query Chain B RPC"""
    
    def __init__(self, rpc_url: str):
        self.rpc_url = rpc_url
    
    def get_latest_block(self):
        """Get latest block from Chain B"""
        response = requests.get(f"{self.rpc_url}/api/latest-block")
        if response.ok:
            return response.json()
        return None
    
    def get_block(self, height: int):
        """Get specific block by height"""
        response = requests.get(f"{self.rpc_url}/api/block/{height}")
        if response.ok:
            return response.json()
        return None
    
    def get_chain_info(self):
        """Get chain info"""
        response = requests.get(f"{self.rpc_url}/api/chain-info")
        if response.ok:
            return response.json()
        return None


class RelayerBot:
    """Relayer bot to sync Chain B blocks to Sepolia LightClient"""
    
    def __init__(self, chain_b_client: ChainBClient, web3: Web3, 
                 light_client_address: str, private_key: str):
        self.chain_b = chain_b_client
        self.web3 = web3
        self.account = Account.from_key(private_key)
        self.light_client = web3.eth.contract(
            address=Web3.to_checksum_address(light_client_address),
            abi=LIGHT_CLIENT_ABI
        )
        
        self.is_running = False
        self.synced_height = 0  # FIX: Start from -1 so first sync gets block 0
        self.polling_interval = 5  # seconds
        
    async def start(self):
        """Start relayer"""
        if self.is_running:
            print("⚠️  Relayer already running")
            return
        
        self.is_running = True
        print("\n🤖 Relayer Bot Started")
        print("=" * 70)
        print(f"   Chain B RPC: {self.chain_b.rpc_url}")
        print(f"   Sepolia RPC: {self.web3.provider.endpoint_uri}")
        print(f"   LightClient: {self.light_client.address}")
        print(f"   Relayer Account: {self.account.address}")
        print(f"   Polling Interval: {self.polling_interval}s")
        print("=" * 70)
        
        # Get current synced height from LightClient
        try:
            contract_height = self.light_client.functions.latestBlockHeight().call()
            current_root = self.light_client.functions.latestValidRoot().call()
            print(f"\n📊 Current State:")
            print(f"   LightClient Height: {contract_height}")
            print(f"   LightClient Root: {current_root.hex()}")
            # Sync from contract's height (if contract has blocks, continue from there)
            self.synced_height = contract_height
        except Exception as e:
            print(f"   ⚠️  Could not read LightClient state: {e}")
            # If contract not deployed or no blocks yet, start from -1 (will sync block 0 first)
            self.synced_height = 0  
        
        # Get Chain B info
        try:
            chain_info = self.chain_b.get_chain_info()
            if chain_info:
                print(f"\n🔗 Chain B Info:")
                print(f"   Chain ID: {chain_info.get('chainId')}")
                print(f"   Block Height: {chain_info.get('blockHeight')}")
                print(f"   Merkle Root: {chain_info.get('merkleRoot')}")
                print(f"   Total Users: {chain_info.get('totalUsers')}")
            else:
                print(f"\n🔗 Chain B Info:")
                print(f"   ⚠️  Could not fetch chain info (Chain B RPC may not be ready)")
        except Exception as e:
            print(f"   ⚠️  Could not read Chain B info: {e}")
        
        print(f"\n⏳ Monitoring Chain B for new blocks...\n")
        
        # Start polling loop
        await self.poll_loop()
    
    def stop(self):
        """Stop relayer"""
        self.is_running = False
        print("\n🛑 Relayer stopped")
    
    async def poll_loop(self):
        """Main polling loop"""
        while self.is_running:
            try:
                await self.check_new_blocks()
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
            
            await asyncio.sleep(self.polling_interval)
    
    async def check_new_blocks(self):
        """Check for new blocks and sync"""
        latest_block = self.chain_b.get_latest_block()
        
        if not latest_block:
            return
        
        chain_b_height = latest_block.get('height', 0)
        
        # Check if there are new blocks
        if chain_b_height <= self.synced_height:
            print(f"⏳ No new blocks. Chain B Height: {chain_b_height}, Synced Height: {self.synced_height}")
            return
        
        print(f"\n🔔 New Block Detected!")
        print(f"   Chain B Height: {chain_b_height}")
        print(f"   Synced Height: {self.synced_height}")
        print(f"   Blocks to Sync: {chain_b_height - self.synced_height}")
        
        # Sync each new block
        # FIX: If synced_height is -1 (initial), start from block 0
        start_height = self.synced_height + 1 if self.synced_height >= 0 else 0
        for height in range(start_height, chain_b_height + 1):
            print(f"\n➡️  Syncing Block #{height}...")
            await self.sync_block(height)
    
    async def sync_block(self, height: int):
        """Sync a specific block to LightClient"""
        print(f"\n📤 Syncing Block #{height}...")
        
        try:
            # Fetch block from Chain B
            block = self.chain_b.get_block(height)
            print(block)
            if not block:
                print(f"   ❌ Could not fetch block #{height}")
                return
            
            print(f"   📥 Fetched from Chain B")
            print(f"      Merkle Root: {block.get('stateRoot')}")
            print(f"      Block Hash: {block.get('blockHash')}")
            print(f"      Signatures: {block.get('signatures')}")
            
            # Prepare BlockHeader struct (matches Solidity struct)
            actual_height = block.get('height')  # Get actual height from block first!
            
            merkle_root = block.get('stateRoot')
            if isinstance(merkle_root, int):
                merkle_root_bytes32 = merkle_root.to_bytes(32, byteorder='big')
            elif isinstance(merkle_root, str) and merkle_root.startswith('0x'):
                merkle_root_bytes32 = bytes.fromhex(merkle_root[2:].zfill(64))
            else:
                merkle_root_bytes32 = bytes(32)
            
            # Get parent hash - use actual_height, not parameter height!
            if actual_height > 0:  # FIX: Use actual_height from block
                prev_block = self.chain_b.get_block(actual_height - 1)
                parent_hash = prev_block.get('blockHash') if prev_block else '0x' + '0' * 64
            else:
                # Genesis block (height=0) has no parent
                parent_hash = '0x' + '0' * 64
            
            if isinstance(parent_hash, str) and parent_hash.startswith('0x'):
                parent_hash_bytes32 = bytes.fromhex(parent_hash[2:].zfill(64))
            else:
                parent_hash_bytes32 = bytes(32)
            
            block_hash = block.get('blockHash')
            if isinstance(block_hash, str) and block_hash.startswith('0x'):
                block_hash_bytes32 = bytes.fromhex(block_hash[2:].zfill(64))
            else:
                block_hash_bytes32 = bytes(32)
            
            # Convert signatures to bytes[]
            signatures = []
            for sig in block.get('signatures', []):
                if isinstance(sig, str):
                    if sig.startswith('0x'):
                        sig = sig[2:]
                    signatures.append(bytes.fromhex(sig))
                elif isinstance(sig, bytes):
                    signatures.append(sig)
            
            # Create BlockHeader tuple (blockHeight, merkleRoot, timestamp, parentHash, blockHash)
            # CRITICAL: Use block's actual height, not the parameter!
            actual_height = block.get('height')
            # FIX: Use fixed timestamp = 0 to match Chain B signing
            timestamp_value = 0
            header_tuple = (
                actual_height,  # FIX: Use block's actual height!
                merkle_root_bytes32,
                timestamp_value,  # Fixed = 0
                parent_hash_bytes32,
                block_hash_bytes32
            )
            
            print(f"   📝 Prepared header:")
            print(f"      Height: {actual_height} (actual from block)")
            print(f"      Merkle Root: 0x{merkle_root_bytes32.hex()}")
            print(f"      Timestamp: {timestamp_value}")
            print(f"      Parent Hash: 0x{parent_hash_bytes32.hex()}")
            print(f"      Block Hash: 0x{block_hash_bytes32.hex()}")
            print(f"      Signatures count: {len(signatures)}")

            packed = b''.join([
                actual_height.to_bytes(32, 'big'),
                merkle_root_bytes32,
                timestamp_value.to_bytes(32, 'big'),
                parent_hash_bytes32,
                block_hash_bytes32
            ])
            from eth_account import Account
            keccak_hash = Web3.keccak(packed)
            print(f"\n🔑 HEADER HASH (Python Calculated): 0x{keccak_hash.hex()}")
            
            # 4. Kiểm tra người ký
            print("\n🕵️ --- SIGNER CHECK ---")
            # Lấy account đầu tiên (Proposer)
            key = os.getenv("VALIDATOR_0_KEY")
            signer_account = Account.from_key(key)  # Cần đặt biến môi trường cho validator đầu tiên
            print(f"Expected Signer Address (from .env): {signer_account.address}")
            
            # Recover thử từ chữ ký đầu tiên
            if block.get('signatures'):
                from eth_account import Account
                from eth_account.messages import encode_defunct
                
                msg = encode_defunct(primitive=keccak_hash)
                recovered = Account.recover_message(msg, signature=signatures[0])
                print(f"Recovered Address (Local Check):   {recovered}")
                
                if recovered.lower() == signer_account.address.lower():
                    print("✅ Local Recovery MATCHES! (Hash logic in Python is consistent)")
                    print("👉 If Solidity fails, check if this address is in the Contract's 'owners' list.")
                else:
                    print("❌ Local Recovery FAILED! (Something is wrong with signing logic)")
                    
            print("-------------------------\n")
            
            # Build transaction
            tx = self.light_client.functions.submitHeader(
                header_tuple,  # BlockHeader struct as tuple
                signatures     # bytes[] array
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
                'gas': 500000,
                'gasPrice': self.web3.eth.gas_price,
            })
            
            # Sign and send
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            print(f"   📤 Submitted to Sepolia: {tx_hash.hex()}")
            print(f"   ⏳ Waiting for confirmation...")
            
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                print(f"   ✅ Synced successfully!")
                print(f"      Gas Used: {receipt['gasUsed']}")
                self.synced_height = height
            else:
                print(f"   ❌ Transaction failed!")
                
        except Exception as e:
            print(f"   ❌ Sync failed: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main entry point"""
    
    # Check configuration
    if not PRIVATE_KEY:
        print("❌ Error: PRIVATE_KEY not set in .env file")
        return
    
    # Initialize clients
    chain_b_client = ChainBClient(CHAIN_B_RPC)
    web3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC))
    
    if not web3.is_connected():
        print(f"❌ Error: Could not connect to Sepolia RPC: {SEPOLIA_RPC}")
        return
    
    print(f"✅ Connected to Sepolia (Chain ID: {web3.eth.chain_id})")
    
    # Create and start relayer
    relayer = RelayerBot(chain_b_client, web3, LIGHT_CLIENT_ADDRESS, PRIVATE_KEY)
    
    try:
        await relayer.start()
    except KeyboardInterrupt:
        relayer.stop()
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
