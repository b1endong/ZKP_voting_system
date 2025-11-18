

import time
import asyncio
from typing import Optional
from dataclasses import asdict
from web3 import Web3
from eth_account import Account

from chain_b import ChainB, BlockHeader


class Relayer:
    """Relayer bot for syncing Chain B headers to Chain A"""
    
    def __init__(self, chain_b: ChainB, light_client_contract, 
                 web3: Web3, account: Account):
        self.chain_b = chain_b
        self.light_client = light_client_contract
        self.web3 = web3
        self.account = account
        
        self.is_running = False
        self.synced_height = 0
        self.polling_interval = 20  # 5 seconds
        
        print('🤖 Relayer initialized')
        print(f'   Chain B: {chain_b.chain_id}')
        print(f'   LightClient: {light_client_contract.address}')
        print(f'   Account: {account.address}')

    async def start(self):
        """Start the relayer"""
        if self.is_running:
            print('⚠️  Relayer already running')
            return

        self.is_running = True
        print('🚀 Relayer started')
        print(f'   Polling every {self.polling_interval}s')
        
        # Get current synced height from LightClient
        try:
            self.synced_height = self.light_client.functions.latestBlockHeight().call()
            print(f'   Starting from height: {self.synced_height}')
        except Exception as e:
            print(f'   Starting from height: 0 (genesis)')
            self.synced_height = 0

        # Start polling loop
        await self.poll_loop()

    def stop(self):
        """Stop the relayer"""
        if not self.is_running:
            return

        self.is_running = False
        print('🛑 Relayer stopped')

    async def poll_loop(self):
        """Main polling loop"""
        while self.is_running:
            try:
                await self.sync_new_blocks()
            except Exception as e:
                print(f'❌ Relayer error: {e}')

            # Wait before next poll
            await asyncio.sleep(self.polling_interval)

    async def sync_new_blocks(self):
        """Sync new blocks from Chain B to Chain A"""
        chain_b_height = self.chain_b.block_height
        
        # Check if there are new blocks
        if chain_b_height <= self.synced_height:
            return

        print(f'\n📡 Relayer: New blocks detected on Chain B')
        print(f'   Chain B height: {chain_b_height}')
        print(f'   Synced height: {self.synced_height}')
        print(f'   Blocks to sync: {chain_b_height - self.synced_height}')

        # Sync each new block sequentially
        for height in range(self.synced_height + 1, chain_b_height + 1):
            await self.sync_block(height)

    async def sync_block(self, height: int):
        """Sync a specific block"""
        print(f'\n🔄 Syncing block #{height}...')

        try:
            # Step 1: Fetch block header from Chain B
            block_header = self.chain_b.get_block_header(height)
            print(f'   📥 Fetched header from Chain B')
            print(f'      Merkle Root: {block_header.merkle_root[:20]}...')
            print(f'      Block Hash: {block_header.block_hash[:20]}...')
            print(f'      Signatures: {len(block_header.validator_signatures)}')

            # Step 2: Format header for smart contract
            header_struct = (
                block_header.block_height,
                block_header.merkle_root,
                block_header.timestamp,
                block_header.parent_hash,
                block_header.block_hash,
                block_header.validator_signature
            )

            # Step 3: Submit to LightClient on Chain A
            print(f'   📤 Submitting to LightClient on Chain A...')
            
            # Build transaction
            tx = self.light_client.submitHeader(
                header_struct
            )
            
            # Sign transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.account.key)
            
            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            print(f'   ⏳ Transaction sent: {tx_hash.hex()}')
            
            # Wait for confirmation
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
            print(f'   ✅ Transaction confirmed (gas used: {receipt.gasUsed})')

            # Step 4: Update synced height
            self.synced_height = height
            
            print(f'   ✅ Block #{height} synced successfully')

        except Exception as e:
            print(f'   ❌ Failed to sync block #{height}: {e}')
            raise

    def get_status(self) -> dict:
        """Get relayer status"""
        return {
            'isRunning': self.is_running,
            'syncedHeight': self.synced_height,
            'chainBHeight': self.chain_b.block_height,
            'blocksBehind': self.chain_b.block_height - self.synced_height,
            'pollingInterval': self.polling_interval
        }

    def set_polling_interval(self, seconds: int):
        """Update polling interval"""
        self.polling_interval = seconds
        print(f'⚙️  Polling interval updated to {seconds}s')


# Synchronous wrapper for easier usage
class RelayerSync:
    """Synchronous wrapper for Relayer"""
    
    def __init__(self, chain_b: ChainB, light_client_contract,
                 web3: Web3, account: Account):
        self.relayer = Relayer(chain_b, light_client_contract, web3, account)
        self.loop = None
        self.task = None

    def start(self):
        """Start the relayer in background"""
        if self.loop is None:
            self.loop = asyncio.new_event_loop()
            
            def run_loop():
                asyncio.set_event_loop(self.loop)
                self.task = self.loop.create_task(self.relayer.start())
                self.loop.run_forever()
            
            import threading
            thread = threading.Thread(target=run_loop, daemon=True)
            thread.start()
            
            # Wait a bit for startup
            time.sleep(1)

    def stop(self):
        """Stop the relayer"""
        if self.loop:
            self.relayer.stop()
            self.loop.call_soon_threadsafe(self.loop.stop)

    def get_status(self):
        """Get status"""
        return self.relayer.get_status()

    def sync_block_now(self, height: int):
        """Manually sync a specific block"""
        if self.loop:
            future = asyncio.run_coroutine_threadsafe(
                self.relayer.sync_block(height), 
                self.loop
            )
            return future.result(timeout=30)


def main():
    """Demo"""
    import hashlib
    from web3 import Web3
    
    print('=' * 60)
    print('Relayer Demo')
    print('=' * 60)
    
    # Create Chain B
    chain_b = ChainB()
    
    # Add some voters and produce blocks
    print('\n📋 Producing blocks on Chain B...')
    chain_b.add_voter('0x' + hashlib.sha256(b'voter1').hexdigest())
    chain_b.produce_block()
    
    chain_b.add_voter('0x' + hashlib.sha256(b'voter2').hexdigest())
    chain_b.produce_block()
    
    # Mock Web3 and LightClient
    print('\n📋 Setting up mock Chain A components...')
    
    # Mock LightClient contract
    class MockLightClient:
        def __init__(self):
            self.address = '0xLightClient0000000000000000000000000001'
            self.latest_height = 0
            
        class Functions:
            def __init__(self, parent):
                self.parent = parent
                
            def latestBlockHeight(self):
                class Call:
                    def __init__(self, height):
                        self.height = height
                    def call(self):
                        return self.height
                return Call(self.parent.latest_height)
            
            def submitHeader(self, header):
                class Builder:
                    def __init__(self, parent, header):
                        self.parent = parent
                        self.header = header
                    def build_transaction(self, params):
                        return {'data': 'mock_tx'}
                return Builder(self.parent, header)
        
        @property
        def functions(self):
            return self.Functions(self)
    
    # Mock Web3
    class MockWeb3:
        class Eth:
            def get_transaction_count(self, address):
                return 0
            @property
            def gas_price(self):
                return 20000000000
            class Account:
                @staticmethod
                def sign_transaction(tx, key):
                    class Signed:
                        rawTransaction = b'mock_raw_tx'
                    return Signed()
            def send_raw_transaction(self, raw_tx):
                return b'mock_tx_hash'
            def wait_for_transaction_receipt(self, tx_hash):
                class Receipt:
                    gasUsed = 150000
                return Receipt()
        eth = Eth()
    
    # Mock account
    class MockAccount:
        address = '0xRelayer00000000000000000000000000000001'
        key = 'mock_private_key'
    
    mock_light_client = MockLightClient()
    mock_web3 = MockWeb3()
    mock_account = MockAccount()
    
    # Create relayer
    relayer = RelayerSync(chain_b, mock_light_client, mock_web3, mock_account)
    
    print('\n📋 Starting relayer...')
    relayer.start()
    
    # Wait and check status
    time.sleep(2)
    print('\n📊 Relayer Status:')
    print(relayer.get_status())
    
    # Produce another block
    print('\n📋 Producing another block on Chain B...')
    chain_b.add_voter('0x' + hashlib.sha256(b'voter3').hexdigest())
    chain_b.produce_block()
    
    # Wait for relayer to sync
    time.sleep(6)
    
    print('\n📊 Final Status:')
    print(relayer.get_status())
    
    relayer.stop()
    print('\n✅ Demo complete')


if __name__ == '__main__':
    main()
