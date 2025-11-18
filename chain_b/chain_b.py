"""
Chain B: Registry AppChain with Multi-Sig Support and Consensus

Complete implementation combining:
- Registry AppChain with Merkle tree state using Poseidon hash
- Proposal-based consensus mechanism for state changes
- Multi-signature validation (M-of-N threshold)
- Ethereum ECDSA signatures for validators
- RPC endpoints for cross-chain queries
- Merkle root calculation for validator consensus

Architecture:
- Chain B is a specialized blockchain for voter registry
- Uses Poseidon hash for Merkle tree (same as Circom circuit)
- CONSENSUS: Validators vote on proposals to add/remove users
- STATE SYNC: All validators maintain identical state
- MULTI-SIG: Block production requires M-of-N validator signatures
- Relayer collects signatures and submits to Chain A
- No merkle proofs generated on Chain B (proofs generated off-chain for voting)

Consensus Flow (Adding a User):
================================
1. Validator A proposes: "Add Alice with secret=123"
2. Proposal broadcast to all validators
3. Validator B votes: "Approve"
4. Validator C votes: "Approve" → Threshold (3-of-5) reached!
5. Proposal executed: All validators add Alice to local state
6. Result: All validators now have IDENTICAL user_data

Block Production Flow (Block Proposer Model):
==============================================
1. All validators have synchronized state (via consensus)
2. PROPOSER (1 validator) builds block:
   - Calculates merkle_root from local user_data
   - Creates BlockHeader(height, merkleRoot, timestamp, ...)
   - Signs header_hash with own private key
   - Broadcasts BlockProposal to other validators
3. OTHER VALIDATORS receive proposal:
   - Recalculate merkle_root from their own user_data
   - Compare: merkleRoot_local == proposal.merkleRoot
   - If MATCH → Sign header_hash → Send signature back to proposer
   - If MISMATCH → REJECT (state desynchronization detected)
4. PROPOSER collects signatures:
   - If threshold reached (e.g., 3-of-5) → Finalize block
   - If threshold NOT reached → Block rejected
5. Finalized block broadcast to all validators

State Change Detection:
========================
Scenario 1 (Correct):
- All validators: users = ["alice", "bob"]
- All calculate: merkle_root = 0x123abc...
- All sign same header_hash
- Threshold reached → Block finalized ✅

Scenario 2 (Desynchronized):
- Validator 1,2: users = ["alice", "bob"] → merkle_root = 0x123abc...
- Validator 3: users = ["alice"] → merkle_root = 0x456def...
- Validator 3 signs different header_hash
- Only 2 matching signatures → Below threshold → Block rejected ❌

Security Guarantees:
====================
1. No single validator can forge state (requires M-of-N consensus)
2. State changes require explicit validator votes
3. Block production verifies state synchronization
4. Byzantine fault tolerance: Up to (N-M) malicious validators tolerated

Example:
    # Initialize chain with 5 validators, 3-of-5 threshold
    chain = ChainB(num_validators=5, threshold=3)
    
    # Propose adding a user (requires consensus)
    # commitment = Poseidon(secret, nullifierTrapdoor)
    commitment = 0x1234...  # Pre-calculated commitment
    proposal = chain.propose_add_user("alice", commitment=commitment, proposer_index=0)
    chain.vote_proposal(proposal, voter_index=1)
    chain.vote_proposal(proposal, voter_index=2)  # Threshold reached, user added!
    
    # Produce block (validators verify state via multi-sig)
    block = chain.produce_block()
    
    # Query merkle root (all validators agree on this value)
    merkle_root = chain.get_merkle_root()
"""

import hashlib
import json
import time
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from circomlibpy.poseidon import PoseidonHash
from dotenv import load_dotenv

# Load environment variables from .env file in parent directory
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=env_path)

PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617

poseidon_hash = PoseidonHash()

def poseidon_hash_1(data):
    """Hash single input using Poseidon (for leaves)"""
    return poseidon_hash.hash(1, [int(data)])

def poseidon_hash_2(left_int, right_int):
    """Hash two inputs using Poseidon (for internal nodes)"""
    return poseidon_hash.hash(2, [int(left_int), int(right_int)])

def hash_func(data):
    """
    Hash function for creating merkle tree leaves.
    Uses Poseidon hash (same as circuit).
    """
    return poseidon_hash_1(data)

# --- CLASS MERKLE TREE (ĐÃ SỬA LỖI) ---

class MerkleTree:
    def __init__(self, data_list, fixed_depth=10):
        """
        Khởi tạo Merkle Tree.
        data_list: Danh sách dữ liệu ban đầu (ví dụ: self.users)
        fixed_depth: Độ sâu cố định của mạch (ví dụ: 10)
        """
        self.fixed_depth = fixed_depth
        
        # 1. Tạo lá (phải là SỐ NGUYÊN)
        self.leaves = [int(data) for data in data_list]
        if not self.leaves:
            self.leaves = [0] # Phải có ít nhất 1 lá (rỗng)
            
        # 2. Xây dựng cây
        self.tree = self._build_merkle_tree()

    def _build_merkle_tree(self):
        """
        Hàm private: Xây dựng cây Merkle (LOGIC THƯA).
        """
        if not self.leaves:
            return [[0]]
        
        tree = [self.leaves]
        
        # GÁN ĐÚNG: current_level là một DANH SÁCH (list)
        current_level = self.leaves
        
        # DÒNG 142 CŨ CỦA BẠN SẼ KHÔNG CÒN LỖI
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if (i + 1) < len(current_level) else 0
                
                parent = 0
                if right == 0:
                    parent = left  # LOGIC QUAN TRỌNG: Đẩy node lên
                else:
                    # SỬA LỖI: Phải dùng hàm băm 2-1 (poseidon_hash_2)
                    parent = poseidon_hash_2(left, right)
                
                next_level.append(parent)
            
            tree.append(next_level)
            current_level = next_level # Gán lại current_level (vẫn là list)
            
        return tree

    def get_root(self):
        """Lấy Merkle Root (là số nguyên)"""
        if not self.tree or not self.tree[-1]:
            return 0
        return self.tree[-1][0]

    def get_proof(self, leaf_index):
        """
        Lấy Merkle proof (LOGIC THƯA + PADDING).
        Trả về (path_elements, path_indices)
        """
        if leaf_index < 0 or leaf_index >= len(self.leaves):
            raise ValueError(f"Invalid leaf index: {leaf_index}")
        
        path_elements = []
        path_indices = []
        current_index = leaf_index
        
        # Lấy proof từ cây (chỉ đến độ cao thực tế của cây)
        for level in range(len(self.tree) - 1): # Trừ mức root
            level_nodes = self.tree[level]
            
            is_right_child = current_index % 2 == 1
            sibling_index = current_index - 1 if is_right_child else current_index + 1
            
            path_indices.append(1 if is_right_child else 0)
            
            sibling_hash = 0
            if sibling_index < len(level_nodes):
                sibling_hash = level_nodes[sibling_index]
            
            path_elements.append(sibling_hash)
            current_index = current_index // 2
            
        # Pad 0 vào proof cho đến khi đủ fixed_depth (bắt buộc cho Circom)
        while len(path_elements) < self.fixed_depth:
            path_elements.append(0)
            path_indices.append(0)
            
        return (path_elements, path_indices)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class IdentityData:
    """User identity data stored on Chain B (compatible with Circom voting circuit)"""
    userId: str
    commitment: int  # Poseidon hash of (secret, nullifierTrapdoor) - NEVER store secret!
    


@dataclass
class BlockHeader:
    """Block header for Solidity contract"""
    blockHeight: int
    merkleRoot: int # Changed to int (field element)
    timestamp: int
    parentHash: bytes
    blockHash: bytes
    
    def to_tuple(self):
        """Convert to tuple for Solidity"""
        # Convert merkleRoot to bytes32 for Solidity
        merkle_root_bytes = self.merkleRoot.to_bytes(32, 'big')
        return (
            self.blockHeight,
            merkle_root_bytes,
            self.timestamp,
            self.parentHash,
            self.blockHash
        )


@dataclass
class BlockProposal:
    """Block proposal broadcast by proposer to validators"""
    header: BlockHeader
    proposer_index: int  # Index of validator who proposed
    proposer_signature: bytes


@dataclass
class Block:
    """Complete block with multi-sig"""
    height: int
    stateRoot: int  # Merkle root as field element
    timestamp: int
    parentHash: str
    blockHash: str
    signatures: List[bytes]
    valid_signature_count: int
    proposer_index: int  # Track which validator proposed this block
    
    def to_solidity_header(self) -> BlockHeader:
        """Convert to Solidity BlockHeader format"""
        return BlockHeader(
            blockHeight=self.height,
            merkleRoot=self.stateRoot,  # Already an int (field element)
            timestamp=self.timestamp,
            parentHash=bytes.fromhex(self.parentHash[2:]) if self.parentHash.startswith('0x') else bytes.fromhex(self.parentHash),
            blockHash=bytes.fromhex(self.blockHash[2:]) if self.blockHash.startswith('0x') else bytes.fromhex(self.blockHash)
        )


# ============================================================================
# MULTI-SIG HELPER
# ============================================================================

class MultiSigHelper:
    """Helper for multi-signature operations"""
    
    def __init__(self, validator_accounts: List[Account], threshold: int):
        self.validators = validator_accounts
        self.threshold = threshold
        self.n = len(validator_accounts)
        
        if threshold <= 0 or threshold > self.n:
            raise ValueError(f"Invalid threshold {threshold} for {self.n} validators")
    
    def create_header_hash(self, header: BlockHeader) -> bytes:
        """Create Keccak256 hash of block header (matches Solidity)"""
        # Convert merkleRoot to bytes if it's an int
        if isinstance(header.merkleRoot, int):
            merkle_root_bytes = header.merkleRoot.to_bytes(32, 'big')
        else:
            merkle_root_bytes = header.merkleRoot
        
        packed = b''.join([
            header.blockHeight.to_bytes(32, 'big'),
            merkle_root_bytes,
            header.timestamp.to_bytes(32, 'big'),
            header.parentHash,
            header.blockHash
        ])
        return Web3.keccak(packed)
    
    def sign_header(self, header_hash: bytes, validator: Account) -> bytes:
        """Sign header hash with Ethereum personal_sign"""
        message = encode_defunct(primitive=header_hash)
        signed = validator.sign_message(message)
        return signed.signature
    
    def collect_signatures(self, header_hash: bytes, min_sigs: int = None) -> List[bytes]:
        """Collect signatures from validators"""
        if min_sigs is None:
            min_sigs = self.threshold
        
        signatures = []
        for i in range(min_sigs):
            validator = self.validators[i]
            sig = self.sign_header(header_hash, validator)
            signatures.append(sig)
        
        return signatures
    
    def verify_multisig(self, header_hash: bytes, signatures: List[bytes]) -> Tuple[bool, int, List[str]]:
        """Verify multi-signature"""
        message = encode_defunct(primitive=header_hash)
        valid_signers = []
        seen_signers = set()
        validator_addresses = {acc.address.lower() for acc in self.validators}
        
        for sig in signatures:
            try:
                recovered = Account.recover_message(message, signature=sig)
                recovered_lower = recovered.lower()
                
                if recovered_lower not in validator_addresses:
                    continue
                if recovered_lower in seen_signers:
                    continue
                
                valid_signers.append(recovered)
                seen_signers.add(recovered_lower)
            except:
                continue
        
        valid_count = len(valid_signers)
        is_valid = valid_count >= self.threshold
        return is_valid, valid_count, valid_signers
    
    def get_validator_addresses(self) -> List[str]:
        """Get list of validator addresses"""
        return [acc.address for acc in self.validators]


# ============================================================================
# CONSENSUS MECHANISM
# ============================================================================

@dataclass
class StateProposal:
    """Proposal for state change (add/remove user)"""
    proposalId: str
    action: str  # "add" or "remove"
    userId: str
    userData: Optional[IdentityData]  # None for remove action
    proposer: str
    timestamp: int
    votes: List[str]  # List of validator addresses who voted
    
    def is_approved(self, threshold: int) -> bool:
        """Check if proposal has enough votes"""
        return len(self.votes) >= threshold


# ============================================================================
# CHAIN B
# ============================================================================

class ChainB:
    """Chain B: Registry AppChain with Multi-Sig and Consensus"""
    
    def __init__(
        self, 
        num_validators: int = 5,
        threshold: int = 3,
        chain_id: str = "registry-chain-1",
        merkle_depth: int = 10
    ):
        self.chain_id = chain_id
        self.num_validators = num_validators
        self.threshold = threshold
        self.merkle_depth = merkle_depth
        
        # State
        self.blocks = []
        self.height = 0
        self.create_genesis_block()
        self.users: Dict[str, IdentityData] = {}
        self.user_list: List[str] = []  # Track insertion order
        self.merkle_tree: Optional[MerkleTree] = None
        self.merkle_root = 0  # Field element (int)
        
        # Consensus state
        self.pending_proposals: Dict[str, StateProposal] = {}
        self.proposal_counter = 0
        
        # Block proposer (round-robin rotation)
        self.current_proposer = 0  # Index of validator who proposes next block
        
        # Initialize validators
        self._initialize_validators()
        
        print(f"🌐 Chain B initialized")
        print(f"   Chain ID: {self.chain_id}")
        print(f"   Validators: {self.num_validators}")
        print(f"   Threshold: {self.threshold}-of-{self.num_validators}")
        print(f"   Merkle Depth: {self.merkle_depth} (max {2**self.merkle_depth} users)")
    
    def create_genesis_block(self):
        """Create genesis block with empty state"""
        genesis_header = BlockHeader(
            blockHeight=0,
            merkleRoot=0,
            timestamp=0,
            parentHash=b'\x00' * 32,
            blockHash=b'\x00' * 32
        )
        genesis_block = Block(
            self.height,
            stateRoot=0,
            timestamp=genesis_header.timestamp,
            parentHash='0x' + genesis_header.parentHash.hex(),
            blockHash='0x' + genesis_header.blockHash.hex(),
            signatures=[],
            valid_signature_count=0,
            proposer_index=-1
        )
        self.blocks.append(genesis_block)
        self.height += 1
        print("🧱 Genesis block created")

    def _initialize_validators(self):
        """Create validator accounts with Ethereum keypairs from .env"""
        # Load validator private keys from environment variables
        validator_private_keys = []
        for i in range(self.num_validators):
            key = os.getenv(f'VALIDATOR_{i}_KEY')
            if not key:
                raise ValueError(f"Missing VALIDATOR_{i}_KEY in .env file")
            # Ensure key has 0x prefix
            if not key.startswith('0x'):
                key = '0x' + key
            validator_private_keys.append(key)
        
        # Create accounts from private keys
        self.validator_accounts = [Account.from_key(pk) for pk in validator_private_keys]
        
        print("🔑 Validator addresses loaded from .env:")
        for i, acc in enumerate(self.validator_accounts):
            print(f"   Validator {i}: {acc.address}")
            # Debug: Show first few chars of private key to verify
            print(f"      Private key: {acc.key.hex()[:20]}...")
        
        self.multisig_helper = MultiSigHelper(self.validator_accounts, self.threshold)
    
    def register_user(self, userId: str, commitment: int) -> IdentityData:
        """Register a new user (compatible with Circom circuit)
        
        IMPORTANT: State Synchronization Flow
        ======================================
        1. ALL validators must have IDENTICAL user_data before producing block
        2. User registration happens OFF-CHAIN (e.g., via API, sync protocol)
        3. Validators independently calculate merkle_root from same user_data
        4. When produce_block() is called:
           - Each validator calculates merkle_root from their local user_data
           - Each validator signs header with their calculated merkle_root
           - If merkle_roots don't match → signatures won't reach threshold → block rejected
        5. Multi-sig consensus ensures all validators agree on the SAME state
        
        Example Flow:
        -------------
        Validator 1: register_user("alice", commitment_X) → merkle_root = X
        Validator 2: register_user("alice", commitment_X) → merkle_root = X (same!)
        Validator 3: register_user("alice", commitment_X) → merkle_root = X (same!)
        → All sign block → Threshold reached → Block finalized
        
        If Validator 3 has different data:
        Validator 3: register_user("alice", commitment_Y) → merkle_root = Y (different!)
        → Validator 3 signs different header_hash → Only 2 signatures → REJECTED
        
        Args:
            userId: User identifier
            commitment: Poseidon hash of (secret, nullifierTrapdoor)
            
        Returns:
            IdentityData: Registered user
        """
        if userId in self.users:
            print(f"⚠️  User {userId} already exists, updating...")
        
        user = IdentityData(userId=userId, commitment=commitment)
        self.users[userId] = user
        if userId not in self.user_list:
            self.user_list.append(userId)
        print(f"📝 Registered user: {userId} (commitment: {hex(commitment)})")
        return user
    
    def remove_user(self, userId: str) -> bool:
        """Remove a user from registry
        
        IMPORTANT: Same synchronization requirements as register_user()
        All validators must remove the same user to maintain consensus.
        
        Args:
            userId: User identifier to remove
            
        Returns:
            bool: True if user was removed, False if user not found
        """
        if userId not in self.users:
            print(f"⚠️  User {userId} not found")
            return False
        
        del self.users[userId]
        self.user_list.remove(userId)
        print(f"🗑️  Removed user: {userId}")
        return True
    
    # ========================================================================
    # CONSENSUS METHODS
    # ========================================================================
    
    def propose_add_user(self, userId: str, commitment: int, proposer_index: int = 0) -> str:
        """Propose adding a new user (requires validator consensus)
        
        Consensus Flow:
        1. Validator proposes state change
        2. Proposal is broadcast to all validators
        3. Each validator votes on proposal
        4. If threshold votes reached → execute state change
        5. All validators now have identical state
        
        Args:
            userId: User identifier
            commitment: Poseidon hash of (secret, nullifierTrapdoor)
            proposer_index: Index of proposing validator (0 to num_validators-1)
            
        Returns:
            str: Proposal ID
        """
        self.proposal_counter += 1
        proposal_id = f"add-{userId}-{self.proposal_counter}"
        
        proposer_address = self.validator_accounts[proposer_index].address
        user_data = IdentityData(userId=userId, commitment=commitment)
        
        proposal = StateProposal(
            proposalId=proposal_id,
            action="add",
            userId=userId,
            userData=user_data,
            proposer=proposer_address,
            timestamp=int(time.time() * 1000),
            votes=[proposer_address]  # Proposer auto-votes
        )
        
        self.pending_proposals[proposal_id] = proposal
        print(f"📋 Proposal {proposal_id}: Add user {userId}")
        print(f"   Proposer: {proposer_address[:10]}...")
        print(f"   Votes: 1/{self.threshold}")
        
        return proposal_id
    
    def propose_remove_user(self, userId: str, proposer_index: int = 0) -> str:
        """Propose removing a user (requires validator consensus)
        
        Args:
            userId: User identifier to remove
            proposer_index: Index of proposing validator
            
        Returns:
            str: Proposal ID
        """
        self.proposal_counter += 1
        proposal_id = f"remove-{userId}-{self.proposal_counter}"
        
        proposer_address = self.validator_accounts[proposer_index].address
        
        proposal = StateProposal(
            proposalId=proposal_id,
            action="remove",
            userId=userId,
            userData=None,
            proposer=proposer_address,
            timestamp=int(time.time() * 1000),
            votes=[proposer_address]
        )
        
        self.pending_proposals[proposal_id] = proposal
        print(f"📋 Proposal {proposal_id}: Remove user {userId}")
        print(f"   Proposer: {proposer_address[:10]}...")
        print(f"   Votes: 1/{self.threshold}")
        
        return proposal_id
    
    def vote_proposal(self, proposal_id: str, voter_index: int) -> bool:
        """Validator votes on a proposal
        
        Args:
            proposal_id: Proposal to vote on
            voter_index: Index of voting validator
            
        Returns:
            bool: True if proposal executed (threshold reached)
        """
        if proposal_id not in self.pending_proposals:
            print(f"⚠️  Proposal {proposal_id} not found")
            return False
        
        proposal = self.pending_proposals[proposal_id]
        voter_address = self.validator_accounts[voter_index].address
        
        # Check if already voted
        if voter_address in proposal.votes:
            print(f"⚠️  Validator {voter_address[:10]}... already voted")
            return False
        
        # Add vote
        proposal.votes.append(voter_address)
        vote_count = len(proposal.votes)
        print(f"✅ Vote received from {voter_address[:10]}...")
        print(f"   Votes: {vote_count}/{self.threshold}")
        
        # Check if threshold reached
        if proposal.is_approved(self.threshold):
            self._execute_proposal(proposal)
            del self.pending_proposals[proposal_id]
            return True
        
        return False
    
    def _execute_proposal(self, proposal: StateProposal):
        """Execute approved proposal (internal)"""
        print(f"\n🎯 Executing proposal {proposal.proposalId}")
        print(f"   Action: {proposal.action}")
        print(f"   User: {proposal.userId}")
        
        if proposal.action == "add":
            user = proposal.userData
            self.users[user.userId] = user
            if user.userId not in self.user_list:
                self.user_list.append(user.userId)
            print(f"   ✅ User {user.userId} added to registry")
            
        elif proposal.action == "remove":
            if proposal.userId in self.users:
                del self.users[proposal.userId]
                self.user_list.remove(proposal.userId)
                print(f"   ✅ User {proposal.userId} removed from registry")
            else:
                print(f"   ⚠️  User {proposal.userId} not found")
        
        print(f"   Total users: {len(self.users)}")
    
    def get_pending_proposals(self) -> List[StateProposal]:
        """Get all pending proposals"""
        return list(self.pending_proposals.values())
    
    # ========================================================================
    # BLOCK PRODUCTION
    # ========================================================================
    
    def produce_block(self) -> Block:
        """Produce new block with proposer + multi-sig approval model
        
        Block Production Flow (Proposer Model):
        ========================================
        1. Current proposer (round-robin) builds block:
           - Calculates merkle_root from local user_data
           - Creates BlockHeader
           - Signs header_hash
           - Broadcasts BlockProposal to other validators
        
        2. Other validators verify proposal:
           - Recalculate merkle_root from their own local user_data
           - Compare: merkleRoot_local == proposal.header.merkleRoot
           - If MATCH → Sign header_hash (agree on state)
           - If MISMATCH → REJECT (state desynchronization)
        
        3. Proposer collects signatures:
           - If threshold reached → Block finalized
           - If threshold NOT reached → Block rejected
        
        4. Proposer rotates to next validator (round-robin)
        
        Returns:
            Block: Finalized block with validator signatures
        """
        proposer_index = self.current_proposer
        print(f"\n🔨 Producing block #{self.height}...")
        print(f"   📢 Proposer: Validator {proposer_index}")
        
        # Step 1: PROPOSER builds block
        # Update Merkle tree with Poseidon hash
        if self.users:
            print(self.users)
            # Extract user commitments as list (matching calcInput.js: leaves = users.map(u => u.commitment))
            user_commitments = [user.commitment for user in self.users.values()]
            self.merkle_tree = MerkleTree(user_commitments)
            self.merkle_root = self.merkle_tree.get_root()
        else:
            self.merkle_root = 0
        
        print(f"   📊 Merkle Root: {self.merkle_root}")
        print(f"   👥 Total users: {len(self.users)}")
        
        # Create block header
        # FIX: Use fixed timestamp = 0 to avoid timing issues between signing and relaying
        parent_hash = self.blocks[-1].blockHash if self.blocks else '0x' + '0' * 64
        
        # Block hash includes merkle root as field element
        preimage = f"{self.height}{self.merkle_root}{0}{parent_hash}"
        block_hash = '0x' + hashlib.sha256(preimage.encode()).hexdigest()
        
        # Create header for signing
        header = BlockHeader(
            blockHeight=self.height,
            merkleRoot=self.merkle_root,  # Field element (int)
            timestamp=0,  # Fixed = 0
            parentHash=bytes.fromhex(parent_hash[2:]),
            blockHash=bytes.fromhex(block_hash[2:])
        )
        
        # Proposer signs first
        header_hash = self.multisig_helper.create_header_hash(header)
        
        print(f"\n   🔐 === SIGNING DEBUG ===")
        print(f"   Header being signed:")
        print(f"      blockHeight: {header.blockHeight}")
        print(f"      merkleRoot (int): {header.merkleRoot}")
        print(f"      merkleRoot (bytes32): 0x{header.merkleRoot.to_bytes(32, 'big').hex()}")
        print(f"      timestamp: {header.timestamp}")
        print(f"      parentHash: 0x{header.parentHash.hex()}")
        print(f"      blockHash: 0x{header.blockHash.hex()}")
        print(f"   Header Hash: 0x{header_hash.hex()}")
        
        proposer_account = self.validator_accounts[proposer_index]
        print(f"   Signing with: {proposer_account.address}")
        proposer_signature = self.multisig_helper.sign_header(header_hash, proposer_account)
        print(f"   Signature: 0x{proposer_signature.hex()[:40]}...")
        print(f"   === END DEBUG ===\n")
        
        # Step 2: Broadcast to other validators (simulated)
        print(f"   📡 Broadcasting proposal to validators...")
        proposal = BlockProposal(
            header=header,
            proposer_index=proposer_index,
            proposer_signature=proposer_signature
        )
        
        # Step 3: Collect signatures from other validators
        print(f"   🔐 Collecting {self.threshold}-of-{self.num_validators} signatures...")
        signatures = [proposer_signature]  # Start with proposer's signature
        
        # Other validators verify and sign
        for i in range(self.num_validators):
            if i == proposer_index:
                continue  # Skip proposer (already signed)
            
            # Simulate validator verification:
            # In real system, each validator independently:
            # 1. Receives BlockProposal
            # 2. Recalculates merkle_root from own user_data
            # 3. Compares with proposal.header.merkleRoot
            # 4. If match → sign, if mismatch → reject
            
            # For demo, all validators have same state (from consensus)
            # so they all approve
            if len(signatures) < self.threshold:
                validator_account = self.validator_accounts[i]
                sig = self.multisig_helper.sign_header(header_hash, validator_account)
                signatures.append(sig)
                print(f"      ✅ Validator {i} approved")
        
        # Step 4: Verify threshold reached
        is_valid, valid_count, signers = self.multisig_helper.verify_multisig(header_hash, signatures)
        if not is_valid:
            print(f"   ❌ Block rejected: Only {valid_count}/{self.threshold} signatures")
            print(f"   ⚠️  State desynchronization detected!")
            raise ValueError(f"Multi-sig verification failed: {valid_count}/{self.threshold}")
        
        # Step 5: Finalize block
        block = Block(
            height=self.height,  # FIX: Must match the header that was signed!
            stateRoot=self.merkle_root,
            timestamp=0,
            parentHash=parent_hash,
            blockHash=block_hash,
            signatures=signatures,
            valid_signature_count=valid_count,
            proposer_index=proposer_index
        )
        
        self.blocks.append(block)
        
        print(f"   ✅ Block #{self.height} finalized")
        print(f"   ✍️  Signed by {valid_count} validators")
        
        # Increment height for next block
        self.height += 1
        
        # Step 6: Rotate proposer (round-robin)
        self.current_proposer = (self.current_proposer + 1) % self.num_validators
        
        print(f"   🔄 Next proposer: Validator {self.current_proposer}")
        print(f"   📈 Next block will be #{self.height}")
        
        return block
    
    def query_user(self, userId: str) -> Optional[IdentityData]:
        """Query user by ID"""
        return self.users.get(userId)
    
    def get_merkle_root(self) -> int:
        """Get current merkle root
        
        This is the root that validators verify via multi-sig.
        No merkle proofs are generated on Chain B.
        """
        return self.merkle_root
    
    def get_block(self, height: int) -> Block:
        """Get block at height"""
        if height < 0 or height > self.height:
            raise ValueError(f"Invalid block height: {height}")
        return self.blocks[height]
    
    def get_latest_block(self) -> Optional[Block]:
        """Get latest block"""
        return self.blocks[-1] if self.blocks else None
    
    def get_validator_addresses(self) -> List[str]:
        """Get validator addresses for contract deployment"""
        return self.multisig_helper.get_validator_addresses()
    
    def get_config(self) -> dict:
        """Get configuration for LightClientMultiSig deployment"""
        return {
            'validators': self.get_validator_addresses(),
            'threshold': self.threshold,
            'num_validators': self.num_validators
        }
    
    def format_for_solidity(self, block: Block) -> Dict:
        """Format block for Solidity submitHeader() call"""
        header = block.to_solidity_header()
        return {
            'header': header.to_tuple(),
            'signatures': ['0x' + sig.hex() for sig in block.signatures]
        }
    
    def get_info(self) -> Dict:
        """Get chain information"""
        # Latest block height is (self.height - 1) since we increment after producing
        latest_block_height = self.height - 1 if self.blocks else 0
        
        return {
            'chainId': self.chain_id,
            'blockHeight': latest_block_height,
            'merkleRoot': self.merkle_root,
            'merkleRootHex': hex(self.merkle_root) if self.merkle_root else '0x0',
            'totalUsers': len(self.users),
            'validators': self.num_validators,
            'threshold': self.threshold,
            'merkleDepth': self.merkle_depth,
            'maxUsers': 2 ** self.merkle_depth,
            'merkleTree': {
                'leaves': self.merkle_tree.leaves if self.merkle_tree else [],
                'tree': self.merkle_tree.tree if self.merkle_tree else []   
            }
        }
    
    def get_path(self, user_id: str) -> Dict:
        """Get merkle path for a user (for off-chain ZKP generation)
        
        This is used by Voter Client to get merkle proof without revealing secret.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict with path_elements and path_indices
        """
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found in registry")
        
        if not self.merkle_tree:
            raise ValueError("Merkle tree not initialized")
        
        # Find leaf index
        leaf_index = self.user_list.index(user_id)
        
        # Get proof from merkle tree
        path_elements, path_indices = self.merkle_tree.get_proof(leaf_index)
        
        return {
            'userId': user_id,
            'leafIndex': leaf_index,
            'merkleRoot': self.merkle_root,
            'pathElements': path_elements,
            'pathIndices': path_indices
        }


# ============================================================================
# DEMO
# ============================================================================

def demo():
    """Demo Chain B with multi-sig, consensus, and Poseidon Merkle tree"""
    print("=" * 80)
    print("Chain B: Registry AppChain with Consensus & Multi-Sig Demo")
    print("=" * 80)
    
    # 1. Initialize Chain B (depth=2 means max 4 users, like Circom demo)
    print("\n1️⃣  Initializing Chain B (5 validators, 3-of-5 threshold, depth=2)...")
    chain = ChainB(num_validators=5, threshold=3, merkle_depth=2)
    
    # 2. Show validator configuration
    print("\n2️⃣  Validator Configuration for Updater.sol:")
    config = chain.get_config()
    print(f"   Constructor parameters:")
    print(f"      address[] memory _owners = [")
    for addr in config['validators']:
        print(f"         {addr},")
    print(f"      ];")
    print(f"      uint256 _threshold = {config['threshold']};")
    
    # 3. CONSENSUS DEMO: Propose and vote to add users
    print("\n3️⃣  CONSENSUS: Proposing to add Alice...")
    print("   Validator 0 proposes to add Alice")
    # Calculate commitment: Poseidon(567, 890)
    from circomlibpy.poseidon import PoseidonHash
    poseidon = PoseidonHash()
    alice_commitment = poseidon.hash(2, [567, 890])
    proposal1 = chain.propose_add_user(
        userId="alice",
        commitment=alice_commitment,
        proposer_index=0
    )
    
    print("\n   Other validators vote on proposal...")
    chain.vote_proposal(proposal1, voter_index=1)  # Validator 1 votes
    executed = chain.vote_proposal(proposal1, voter_index=2)  # Validator 2 votes → Threshold reached!
    
    if executed:
        print(f"   🎉 Proposal executed! Alice added to registry")
    
    # 4. Add Bob via consensus
    print("\n4️⃣  CONSENSUS: Proposing to add Bob...")
    bob_commitment = poseidon.hash(2, [678, 901])
    proposal2 = chain.propose_add_user(
        userId="bob",
        commitment=bob_commitment,
        proposer_index=0
    )
    chain.vote_proposal(proposal2, voter_index=1)
    chain.vote_proposal(proposal2, voter_index=2)
    
    # 5. Produce genesis block
    print("\n5️⃣  Producing genesis block (all validators have same state)...")
    genesis = chain.produce_block()
    
    # 6. Add Charlie via consensus
    print("\n6️⃣  CONSENSUS: Proposing to add Charlie...")
    charlie_commitment = poseidon.hash(2, [789, 12])
    proposal3 = chain.propose_add_user(
        userId="charlie",
        commitment=charlie_commitment,
        proposer_index=1
    )
    chain.vote_proposal(proposal3, voter_index=0)
    chain.vote_proposal(proposal3, voter_index=2)
    
    # 7. Produce block 2
    print("\n7️⃣  Producing block 2...")
    block2 = chain.produce_block()
    
    # 8. Demo: Add Dave via consensus
    print("\n8️⃣  CONSENSUS: Proposing to add Dave...")
    dave_commitment = poseidon.hash(2, [890, 123])
    proposal4 = chain.propose_add_user(
        userId = "dave",
        commitment=dave_commitment,
        proposer_index=0
    )
    chain.vote_proposal(proposal4, voter_index=4)
    chain.vote_proposal(proposal4, voter_index=1)
    
    # 9. Produce block 3
    block3 = chain.produce_block()
    
    # 11. Get Merkle root
    print("\n1️⃣1️⃣  Getting Merkle root...")
    merkle_root = chain.get_merkle_root()
    print(f"\n   🌳 Merkle Root: {merkle_root}")
    print(f"      This root is verified by {chain.threshold}-of-{chain.num_validators} validators")
    print(f"      All validators calculated the SAME root → Consensus achieved!")
    print(f"      Merkle proofs are generated OFF-CHAIN for voting (not on Chain B)")
    
    
    # 12. Format for Solidity
    print("\n1️⃣2️⃣  Formatting block 3 for Solidity...")
    solidity_data = chain.format_for_solidity(block3)
    print(f"   ✅ Ready for submitHeader(header, signatures)")
    print(f"      header.blockHeight = {solidity_data['header'][0]}")
    print(f"      header.merkleRoot = {solidity_data['header'][1].hex()}")
    print(f"      signatures = {(solidity_data['signatures'])}")
    
    # 13. Show chain info
    print("\n1️⃣3️⃣  Chain B Status:")
    info = chain.get_info()
    print(info)
    
    print("\n" + "=" * 80)
    print("Demo Complete! ✅")
    print("=" * 80)
    print("\n📋 Key Points:")
    print("   ✅ CONSENSUS: Validators vote on state changes (add/remove users)")
    print("   ✅ MULTI-SIG: Block production requires M-of-N validator signatures")
    print("   ✅ STATE SYNC: All validators have identical state → same merkle_root")
    print("   ✅ Poseidon hash (same as Circom circuit)")
    print("   ✅ No merkle proofs on Chain B (generated off-chain for voting)")
    print("   ✅ User secrets ready for off-chain ZK proof generation")
    print("\n📋 Next Steps:")
    print("   1. Deploy Updater.sol with validator addresses")
    print("   2. Use proof data to generate ZK proofs with Circom circuit")
    print("   3. Submit votes with cross-chain verification")
    print("=" * 80)


if __name__ == '__main__':
    demo()
