# 🏛️ Cross-Chain ZKP Voting System

<div align="center">

![Solidity](https://img.shields.io/badge/Solidity-^0.8.27-363636?logo=solidity)
![Circom](https://img.shields.io/badge/Circom-2.0.0-purple)
![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![Node.js](https://img.shields.io/badge/Node.js-18+-green?logo=node.js)

**Privacy-preserving voting with AppChain + Light Client Bridge architecture**

[Architecture](#-architecture) • [Quick Start](#-quick-start) • [Documentation](./ARCHITECTURE.md)

</div>

---

## 🎯 Overview

Hệ thống bỏ phiếu phi tập trung sử dụng **Zero-Knowledge Proofs** và **Multi-Chain Architecture**:

-   **Chain B (Registry AppChain)**: Quản lý danh sách cử tri với Poseidon Merkle tree + Multi-sig consensus
-   **Chain A (Voting Chain - Sepolia)**: Xác minh bằng chứng ZKP và ghi nhận phiếu bầu
-   **Relayer**: Đồng bộ block headers từ Chain B sang Chain A
-   **ZKP Circuit**: Chứng minh tư cách cử tri mà không tiết lộ danh tính

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    CHAIN A (Sepolia Testnet)                          │
│  ┌──────────────────────┐         ┌──────────────────────┐          │
│  │  Voting Contract     │◄────────│  Updater (Light      │          │
│  │                      │  query  │  Client)             │          │
│  │  • Verify ZK proof   │  root   │                      │          │
│  │  • Check nullifier   │         │  • Store merkle roots│          │
│  │  • Prevent double    │         │  • Verify multi-sig  │          │
│  │    voting            │         │  • 3-of-5 threshold  │          │
│  │  • Tally results     │         │                      │          │
│  └──────────────────────┘         └──────────┬───────────┘          │
└────────────────────────────────────────────────┼──────────────────────┘
                                                 │
                                      ┌──────────▼──────────┐
                                      │  Relayer (Python)   │
                                      │                     │
                                      │  • Poll Chain B     │
                                      │  • Submit headers   │
                                      │  • Gas management   │
                                      └──────────┬──────────┘
                                                 │
┌────────────────────────────────────────────────┼──────────────────────┐
│                 CHAIN B (Registry AppChain)                            │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  Validator Consensus (3-of-5 Multi-Sig)                         │  │
│  │  • Validator 0, 1, 2, 3, 4                                      │  │
│  │  • Proposal-based voting for state changes                      │  │
│  │  • Block proposer rotation (round-robin)                        │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                 ↓                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  Voter Registry (IdentityData)                                  │  │
│  │  • userId → commitment mapping                                  │  │
│  │  • commitment = Poseidon(secret, nullifierTrapdoor)            │  │
│  │  • Secret NEVER stored on-chain                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                 ↓                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  Poseidon Merkle Tree (Depth = 10)                              │  │
│  │  • Leaves: [commitment1, commitment2, ...]                      │  │
│  │  • Root verified by validators via multi-sig                    │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                 ↓                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  Block Production (Signed by 3+ validators)                     │  │
│  │  • blockHeight, merkleRoot, timestamp, parentHash, blockHash    │  │
│  │  • signatures: [sig1, sig2, sig3] (ECDSA)                       │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  📡 RPC Server (Flask - Port 5000)                                     │
│  • /get_merkle_root, /get_merkle_proof, /produce_block                │
│  • /submit_transaction (add/remove voter via consensus)               │
│  • /get_voters, /calculate_commitment                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                 ↑
                      ┌──────────┴──────────┐
                      │                     │
            ┌─────────▼──────────┐   ┌─────▼──────────────┐
            │  Admin Portal      │   │  Voter Client      │
            │  (add/remove voter)│   │  (submit vote)     │
            └────────────────────┘   └────────────────────┘
```

## 🌟 Key Features

### 🔒 Privacy & Security

-   **Zero-Knowledge Proofs (Groth16)**: Chứng minh tư cách cử tri mà không tiết lộ danh tính
-   **Nullifier System**: Mỗi voter chỉ vote 1 lần (nullifierHash unique per election)
-   **Multi-Sig Consensus**: 3-of-5 validators ký block headers (Byzantine fault tolerance)
-   **Secret Never Leaves Client**: Secret chỉ dùng để generate proof off-chain
-   **Poseidon Hash**: ZK-friendly hash function cho Merkle tree

### 🌐 Decentralization

-   **AppChain Architecture**: Tách biệt registry logic khỏi public chain
-   **Permissionless Relayer**: Bất kỳ ai cũng có thể chạy relayer
-   **No Single Point of Trust**: Light client verify multi-sig on-chain
-   **Validator Rotation**: Block proposer xoay vòng công bằng

### ⚡ Scalability & Efficiency

-   **Off-Chain Registry**: Voter management không tốn gas trên Chain A
-   **Efficient Bridge**: Chỉ sync headers (không sync toàn bộ state)
-   **Merkle Proof**: Voter chỉ cần proof path, không cần toàn bộ tree
-   **Gas Optimized**: Smart contracts tối ưu gas consumption

## 🚀 Quick Start

## 🚀 Quick Start

### Prerequisites

```bash
# Required
Python 3.8+
Node.js 18+
MetaMask wallet

# Optional (for contract deployment)
Foundry (forge, anvil)
```

### Installation

```bash
# 1. Clone repository
git clone https://github.com/b1endong/ZKP_voting_system.git
cd zkp_voting_system

# 2. Install Python dependencies
pip install web3 eth-account flask flask-cors circomlibpy python-dotenv

# 3. Setup environment variables
cp .env.example .env
# Edit .env with your keys:
#   SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY
#   PRIVATE_KEY=your_private_key
#   VALIDATOR_PRIVATE_KEYS=key1,key2,key3,key4,key5
```

### Running the System

#### Step 1: Start Chain B (Registry AppChain)

```bash
# Terminal 1: Start Chain B RPC Server
cd chain_b
python chain_b_rpc.py

# Server starts on http://127.0.0.1:5000
# Output shows:
#   🌐 Chain B initialized
#   📊 Validators: 5 (Threshold: 3)
#   🔑 Validator addresses: [0x3C0..., 0xD55..., ...]
```

#### Step 2: Deploy Contracts on Chain A (Sepolia)

```bash
# Terminal 2: Deploy contracts
forge script script/DeployVoting.s.sol:DeployVoting \
    --rpc-url $SEPOLIA_RPC_URL \
    --broadcast \
    --verify

# Save deployed addresses:
#   Verifier: 0x...
#   Updater: 0x...
#   Voting: 0x...
```

#### Step 3: Start Relayer

```bash
# Terminal 3: Start relayer
cd chain_b
python run_relayer.py

# Relayer polls Chain B every 30s and submits headers to Chain A
```

#### Step 4: Use Web Interface

```bash
# Open Admin Portal
# File: front_end/admin_portal/index.html
# Actions:
#   - Connect wallet (must be validator)
#   - Add voters (generate secret → commitment)
#   - Produce blocks

# Open Voter Client
# File: front_end/voter_client/index.html
# Actions:
#   - Enter secret
#   - Generate ZK proof
#   - Submit vote
```

## 📖 Usage Guide

### 1. Admin: Add Voters

```javascript
// Admin Portal workflow:
1. Click "Generate Random Secret" → creates secret (e.g., 123456789)
2. System calculates: commitment = Poseidon(secret, 0)
3. Click "Add Voter" → sends transaction to Chain B
4. Validators vote on proposal (auto-approve in demo)
5. Voter added to registry with commitment
6. ⚠️ Save secret securely! Give it to voter.
```

### 2. Admin: Produce Block

```javascript
// After adding voters:
1. Click "Produce Block"
2. Chain B builds Merkle tree from commitments
3. Validators sign block header (3-of-5 multi-sig)
4. Block finalized with merkleRoot
5. Relayer will sync this block to Chain A
```

### 3. Voter: Submit Vote

```javascript
// Voter Client workflow:
1. Enter secret (received from admin)
2. System fetches merkle proof from Chain B
3. Generate ZK proof off-chain (Circom + snarkjs)
   Proof proves:
   - Voter has valid commitment in merkle tree
   - Without revealing which voter
4. Submit proof + vote to Chain A
5. Smart contract verifies:
   - ZK proof valid
   - Merkle root exists (from Updater)
   - Nullifier not used (prevent double voting)
6. Vote recorded ✅
```

## 📁 Project Structure

```
zkp_voting_system/
├── chain_b/                      # Chain B (Registry AppChain)
│   ├── chain_b.py               # Core blockchain logic
│   │   ├── MerkleTree           # Poseidon-based Merkle tree
│   │   ├── ChainB               # Blockchain with consensus
│   │   └── MultiSigHelper       # Validator signature verification
│   ├── chain_b_rpc.py           # Flask RPC server
│   │   ├── /get_merkle_root     # Query current merkle root
│   │   ├── /get_merkle_proof    # Get proof for commitment
│   │   ├── /submit_transaction  # Add/remove voter via consensus
│   │   ├── /produce_block       # Trigger block production
│   │   └── /get_voters          # List all voters
│   ├── relayer.py               # Relayer core logic
│   └── run_relayer.py           # Relayer daemon
│
├── foundry_contract/            # Solidity Smart Contracts (old version)
└── src/                         # Current Solidity contracts
    ├── Voting.sol               # Main voting contract
    │   ├── submitVote()         # Submit vote with ZK proof
    │   ├── getVoteCount()       # Get results
    │   └── hasVoted()           # Check if nullifier used
    ├── Updater.sol              # Light client (stores merkle roots)
    │   ├── submitHeader()       # Submit Chain B header (relayer)
    │   ├── getRootAtHeight()    # Query merkle root by block height
    │   └── verifySignatures()   # Verify 3-of-5 multi-sig
    └── verifier.sol             # Groth16 ZK verifier (auto-generated)
│
├── zkp_proof/                   # Zero-Knowledge Proof
│   ├── circuit/
│   │   └── voting.circom        # Circom circuit
│   ├── voting.r1cs              # Compiled circuit
│   ├── voting_0001.zkey         # Proving key
│   ├── verification_key.json    # Verification key
│   └── verifier.sol             # Generated verifier
│
├── zkp_interaction/             # ZKP helpers (Node.js)
│   ├── prover.mjs               # Generate proof
│   ├── verifier.mjs             # Verify proof (off-chain)
│   ├── calcInput.js             # Calculate witness
│   └── users.js                 # Demo user data
│
├── front_end/
│   ├── admin_portal/            # Admin interface
│   │   ├── index.html
│   │   ├── admin.js             # Add voters, produce blocks
│   │   └── style.css
│   └── voter_client/            # Voter interface
│       ├── index.html
│       ├── app.js               # Submit votes with ZK proof
│       └── style.css
│
├── script/
│   └── DeployVoting.s.sol       # Foundry deployment script
│
└── test/
    ├── TestVoting.t.sol         # Voting contract tests
    └── TestUpdater.t.sol        # Updater contract tests
```

## 🔬 Technical Deep Dive

### Zero-Knowledge Proof Circuit

```circom
// zkp_proof/circuit/voting.circom
template Voting(merkleDepth) {
    // Private inputs (only voter knows)
    signal input secret;              // Voter's secret
    signal input nullifierTrapdoor;   // For nullifier generation
    signal input pathElements[merkleDepth];
    signal input pathIndices[merkleDepth];

    // Public inputs
    signal input merkleRoot;          // From Chain B (via Updater)
    signal input electionId;
    signal input candidateId;

    // Public output
    signal output nullifierHash;

    // 1. Calculate commitment (leaf in tree)
    component commitment = Poseidon(2);
    commitment.inputs[0] <== secret;
    commitment.inputs[1] <== nullifierTrapdoor;

    // 2. Verify Merkle path
    component merkleProof = MerkleTreeChecker(merkleDepth);
    merkleProof.leaf <== commitment.out;
    merkleProof.root <== merkleRoot;
    for (var i = 0; i < merkleDepth; i++) {
        merkleProof.pathElements[i] <== pathElements[i];
        merkleProof.pathIndices[i] <== pathIndices[i];
    }

    // 3. Generate unique nullifier
    component nullifier = Poseidon(3);
    nullifier.inputs[0] <== secret;
    nullifier.inputs[1] <== nullifierTrapdoor;
    nullifier.inputs[2] <== electionId;
    nullifierHash <== nullifier.out;
}
```

### Chain B Consensus Flow

```python
# Proposal-based consensus for adding voter
def propose_add_user(userId, commitment, proposer_index):
    proposal = StateProposal(
        proposalId=f"add-{userId}-{counter}",
        action="add",
        userId=userId,
        userData=IdentityData(userId, commitment),
        proposer=validators[proposer_index].address,
        votes=[validators[proposer_index].address]  # Auto-vote
    )
    pending_proposals[proposalId] = proposal
    return proposalId

def vote_proposal(proposalId, voter_index):
    proposal = pending_proposals[proposalId]
    proposal.votes.append(validators[voter_index].address)

    if len(proposal.votes) >= threshold:  # e.g., 3 of 5
        # Execute on ALL validators
        execute_proposal(proposal)
        del pending_proposals[proposalId]
        return True
    return False

def execute_proposal(proposal):
    if proposal.action == "add":
        users[proposal.userId] = proposal.userData
        # All validators now have identical state
```

### Block Production with Multi-Sig

```python
def produce_block():
    # 1. Build Merkle tree from commitments
    commitments = [user.commitment for user in users.values()]
    merkle_tree = MerkleTree(commitments, depth=10)
    merkle_root = merkle_tree.get_root()

    # 2. Create block header
    header = BlockHeader(
        blockHeight=current_height,
        merkleRoot=merkle_root,  # Field element (int)
        timestamp=int(time.time()),
        parentHash=previous_block.blockHash,
        blockHash=hash(blockHeight + merkleRoot + timestamp)
    )

    # 3. Proposer signs
    header_hash = keccak256(encode(header))
    eth_signed_hash = eth_sign_hash(header_hash)
    proposer_sig = sign(eth_signed_hash, proposer_privkey)

    # 4. Collect signatures from other validators
    signatures = [proposer_sig]
    for validator in other_validators:
        # Each validator:
        # - Rebuilds merkle tree from own state
        # - Verifies merkle_root matches
        # - Signs if match
        if validator.verify_state(merkle_root):
            sig = validator.sign(eth_signed_hash)
            signatures.append(sig)

    # 5. Finalize if threshold reached
    if len(signatures) >= threshold:
        block = Block(header, signatures)
        blockchain.append(block)
        return block
    else:
        raise ConsensusError("Threshold not reached")
```

### Light Client Verification (Chain A)

```solidity
// src/Updater.sol
function submitHeader(
    BlockHeader calldata header,
    bytes[] calldata signatures
) external {
    require(header.blockHeight > latestBlockHeight, "Old block");

    // 1. Hash header
    bytes32 headerHash = keccak256(abi.encodePacked(
        header.blockHeight,
        header.merkleRoot,
        header.timestamp,
        header.parentHash,
        header.blockHash
    ));

    // 2. Ethereum signed message hash
    bytes32 ethSignedHash = keccak256(abi.encodePacked(
        "\x19Ethereum Signed Message:\n32",
        headerHash
    ));

    // 3. Verify multi-sig
    uint256 validSigs = 0;
    address[] memory signers = new address[](signatures.length);

    for (uint i = 0; i < signatures.length; i++) {
        address signer = ecrecover(ethSignedHash, signatures[i]);
        require(isOwner[signer], "Invalid signer");
        require(!hasSigned[signer], "Duplicate signature");

        signers[i] = signer;
        hasSigned[signer] = true;
        validSigs++;
    }

    require(validSigs >= threshold, "Threshold not met");

    // 4. Store verified root
    validRoots[header.blockHeight] = header.merkleRoot;
    latestBlockHeight = header.blockHeight;

    emit HeaderSubmitted(header.blockHeight, header.merkleRoot);
}
```

## 🧪 Testing

### Test Chain B Locally

```bash
# Start Chain B RPC
cd chain_b
python chain_b_rpc.py

# In another terminal, test endpoints
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/get_merkle_root
```

### Test Contracts on Local Anvil

```bash
# Start local chain
anvil

# Deploy contracts
forge script script/DeployVoting.s.sol \
    --rpc-url http://127.0.0.1:8545 \
    --broadcast

# Run tests
forge test -vvv
```

### Integration Test

```bash
# Full end-to-end test
1. Start Chain B: python chain_b/chain_b_rpc.py
2. Deploy contracts: forge script script/DeployVoting.s.sol --broadcast
3. Start relayer: python chain_b/run_relayer.py
4. Open admin portal: front_end/admin_portal/index.html
5. Add voter → Produce block
6. Open voter client: front_end/voter_client/index.html
7. Submit vote with ZK proof
```

## 🐛 Troubleshooting

### Merkle Root = 0

**Problem**: Chain B produces blocks with `merkleRoot = 0`

**Causes**:

-   Voters added before commitment field was implemented
-   Secret not sent to Chain B (only commitment should be sent)
-   Merkle tree built from wrong data

**Solution**:

1. Restart Chain B RPC server (clears old state)
2. Re-add all voters with correct commitments
3. Verify: commitment = Poseidon(secret, nullifierTrapdoor)

### Commitment Not Found in Registry

**Problem**: Voter client shows "Commitment not found"

**Causes**:

-   Secret incorrect
-   Voter not added to Chain B
-   Block not produced after adding voter

**Solution**:

1. Verify secret matches what admin gave
2. Check voter list in admin portal
3. Click "Produce Block" after adding voters

### Relayer Not Submitting Headers

**Problem**: Headers not appearing on Chain A

**Causes**:

-   Chain B not producing blocks
-   Relayer not running
-   Insufficient gas / nonce issues
-   Wrong contract addresses in relayer config

**Solution**:

1. Check Chain B has blocks: `curl http://127.0.0.1:5000/api/latest-block`
2. Check relayer logs for errors
3. Verify updater contract address in `run_relayer.py`
4. Ensure relayer wallet has ETH for gas

## 📚 Additional Resources

-   **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Detailed system architecture
-   **[FRONTEND_GUIDE.md](./front_end/FRONTEND_GUIDE.md)** - Frontend usage guide
-   **Circom Documentation**: https://docs.circom.io/
-   **Groth16 Paper**: https://eprint.iacr.org/2016/260.pdf
-   **Poseidon Hash**: https://www.poseidon-hash.info/

## 🔗 Related Projects

-   **Semaphore**: ZK identity protocol (similar nullifier concept)
-   **Tornado Cash**: Privacy mixer using ZK proofs
-   **MACI**: Minimal Anti-Collusion Infrastructure for voting
-   **zkSync**: ZK rollup with validity proofs

## 🤝 Contributing

Contributions welcome! Areas for improvement:

-   [ ] Optimize gas costs in Updater contract
-   [ ] Add slashing mechanism for malicious validators
-   [ ] Implement BLS signatures for aggregation
-   [ ] Add economic incentives for relayers
-   [ ] Build mobile app for voters

## 📄 License

MIT License - see [LICENSE](./LICENSE)

## 🙏 Acknowledgments

-   Circom team for ZK circuit tooling
-   Foundry for Solidity development environment
-   Poseidon hash designers for ZK-friendly primitives
-   Ethereum community for infrastructure

---

<div align="center">

**Built with ❤️ for privacy-preserving decentralized voting**

[⭐ Star on GitHub](https://github.com/b1endong/ZKP_voting_system) • [🐛 Report Bug](https://github.com/b1endong/ZKP_voting_system/issues) • [💡 Request Feature](https://github.com/b1endong/ZKP_voting_system/issues)

</div>
-   Inspired by Cosmos, Polkadot, zkSync architectures

## 🙏 Acknowledgments

-   Circom & SnarkJS for ZK tools
-   Foundry for Solidity development
-   Flask for Python RPC server

---

**Status**: ✅ Production-ready simulation  
**Tested on**: Python 3.13, Node.js 18, Windows 11  
**Last updated**: November 15, 2025

cd zkp_proof
circom circuit/voting.circom --r1cs --wasm --sym

# Generate input and run demo

cd input && node calcInput.js
cd ../../ScriptDemo && node DemoScript.js

````

## 📖 Usage

### Voting Process

1. **Generate proof** from your vote + eligibility
2. **Submit to blockchain** with zero-knowledge proof
3. **Vote is counted** anonymously and verifiably

### Code Example

```javascript
// Generate ZK proof
const proof = await groth16.fullProve(voteInput, "voting.wasm", "voting.zkey");

// Submit to contract
await votingContract.submitVote(
    proof.a,
    proof.b,
    proof.c,
    publicSignals,
    commitment
);
````

## 🏗️ Architecture

```
Voter → ZK Circuit → Smart Contract → Blockchain
  ↓         ↓            ↓             ↓
Secret   Generate     Verify       Record
Vote     Proof        Proof        Result
```

**Components:**

-   `voting.circom` - ZK circuit for proof generation
-   `Voting.sol` - Smart contract for verification
-   `verifier.sol` - Groth16 proof verifier
-   `DemoScript.js` - Interactive demo

## 📁 Project Structure

```
├── src/                # Smart contracts
├── zkp_proof/          # ZK circuit & proofs
├── ScriptDemo/         # Demo scripts
├── test/               # Tests
└── script/             # Deploy scripts
```

## 🧪 Testing

```bash
forge test -vv                    # Contract tests
cd zkp_proof && node calcInput.js # Circuit test
```

## 🔐 Security

-   **ZK Privacy**: Votes mathematically hidden
-   **Nullifier Protection**: Prevents double voting
-   **Blockchain Security**: Immutable and transparent
-   **Groth16 Proofs**: Industry-standard ZK system

## 🚀 Deployed Contracts

**Sepolia Testnet:**

-   Voting: `0x8945A98c13228D70C323A9dF051Ee785008fcE17`
-   Verifier: `0x8945A98c13228D70C323A9dF051Ee785008fcE17`

## 🤝 Contributing

1. Fork repo
2. Create feature branch
3. Test changes
4. Submit PR

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

<div align="center">

**⭐ Star if helpful!** • Made with ❤️ for private voting

</div>
