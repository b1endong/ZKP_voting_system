# Kiến Trúc Hệ Thống ZKP Voting với Cross-Chain Verification

## 📋 Tổng Quan

Hệ thống bỏ phiếu sử dụng Zero-Knowledge Proofs (ZKP) với xác minh danh tính cross-chain, đảm bảo:

-   **Privacy**: Bỏ phiếu ẩn danh, không ai biết ai bỏ phiếu cho ai
-   **Integrity**: Không thể vote trùng, mỗi người chỉ vote 1 lần
-   **Verifiability**: Ai cũng có thể verify vote hợp lệ
-   **Decentralization**: Không có single point of failure
-   **Cross-Chain Security**: Danh tính voter được verify từ blockchain khác

---

## 🏗️ Kiến Trúc Tổng Thể

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CHAIN B (Registry Chain)                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Voter Registry (User Database)                                 │ │
│  │  - Alice: secret=567, nullifierTrapdoor=890                     │ │
│  │  - Bob:   secret=678, nullifierTrapdoor=901                     │ │
│  │  - Charlie: secret=789, nullifierTrapdoor=12                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              ↓                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Poseidon Merkle Tree                                           │ │
│  │    Root: 0x123abc...                                            │ │
│  │      ├─ Hash(Alice)                                             │ │
│  │      ├─ Hash(Bob)                                               │ │
│  │      └─ Hash(Charlie)                                           │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              ↓                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Block Header + Multi-Sig                                       │ │
│  │  - blockHeight: 1                                               │ │
│  │  - merkleRoot: 0x123abc...                                      │ │
│  │  - signatures: [sig1, sig2, sig3] (3-of-5 validators)          │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ Relayer
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         CHAIN A (Voting Chain)                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Updater Contract (Light Client)                               │ │
│  │  - Stores verified merkle roots from Chain B                    │ │
│  │  - Validates multi-sig from Chain B validators                  │ │
│  │  - blockHeight → merkleRoot mapping                             │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              ↓                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Voting Contract                                                │ │
│  │  - Verifies ZK proofs                                           │ │
│  │  - Checks merkle root via Updater                               │ │
│  │  - Records votes (nullifier → prevent double voting)            │ │
│  │  - Tallies results                                              │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              ↑
                              │ ZK Proof
                              │
                    ┌─────────────────┐
                    │   Voter (Alice)  │
                    │  - Off-chain     │
                    │  - Circom circuit│
                    └─────────────────┘
```

---

## 🔐 Kiến Trúc ZKP Voting

### 1. **Circom Circuit** (`voting.circom`)

Circuit ZKP chứng minh voter hợp lệ mà không tiết lộ danh tính:

```circom
template Voting(merkleDepth) {
    // Private inputs (chỉ voter biết)
    signal input secret;              // Bí mật của voter
    signal input nullifierTrapdoor;   // Để tạo nullifier
    signal input pathElements[merkleDepth];   // Merkle proof
    signal input pathIndices[merkleDepth];    // Merkle proof directions

    // Public inputs (mọi người thấy)
    signal input merkleRoot;         // Root từ Chain B
    signal input electionId;         // Cuộc bầu cử nào
    signal input candidateId;        // Vote cho ai

    // Public outputs
    signal output nullifierHash;     // Để prevent double voting

    // 1. Verify voter trong Merkle tree
    leaf = poseidonHash1(secret)
    computedRoot = computeMerkleRoot(leaf, pathElements, pathIndices)
    assert(computedRoot == merkleRoot)

    // 2. Generate nullifier
    nullifierHash = poseidonHash3(secret, nullifierTrapdoor, electionId)
}
```

**Tính chất ZKP:**

-   ✅ **Soundness**: Không thể fake proof nếu không phải voter hợp lệ
-   ✅ **Completeness**: Voter hợp lệ luôn tạo được valid proof
-   ✅ **Zero-Knowledge**: Proof không tiết lộ `secret`, `nullifierTrapdoor`, hay vị trí trong tree

### 2. **Groth16 Verifier** (Solidity)

Smart contract verify ZK proof on-chain:

```solidity
contract Groth16Verifier {
    function verifyProof(
        uint[2] memory a,
        uint[2][2] memory b,
        uint[2] memory c,
        uint[1] memory publicSignals  // [nullifierHash]
    ) public view returns (bool);
}
```

**Pairing-based verification:**

-   Kiểm tra: `e(A, B) = e(α, β) · e(C, δ) · e(public_inputs, γ)`
-   Tính toán trên elliptic curve BN128
-   Gas cost: ~250k gas

### 3. **Voting Contract** (Solidity)

```solidity
contract Voting {
    // State
    mapping(uint256 => bool) public nullifierHashes;  // Prevent double voting
    mapping(uint256 => uint256) public voteCounts;    // Tally

    function submitVote(
        uint256[8] memory proof,    // ZK proof
        uint256 blockHeight,        // Chain B block height
        uint256 electionId,
        uint256 candidateId
    ) external {
        // 1. Extract nullifierHash from proof
        uint256 nullifierHash = extractNullifier(proof);

        // 2. Check not double voting
        require(!nullifierHashes[nullifierHash], "Already voted");

        // 3. Get merkle root from Chain B
        bytes32 merkleRoot = updater.getRootAtHeight(blockHeight);
        require(merkleRoot != 0, "Invalid block height");

        // 4. Verify ZK proof
        uint256[1] memory publicSignals = [nullifierHash];
        require(verifier.verifyProof(proof, publicSignals), "Invalid proof");

        // 5. Record vote
        nullifierHashes[nullifierHash] = true;
        voteCounts[candidateId]++;

        emit VoteSubmitted(nullifierHash, candidateId);
    }
}
```

---

## 🌉 Cơ Chế Cross-Chain Communication

### 1. **Chain B Architecture**

#### 1.1 Consensus Mechanism (Thêm/Xóa User)

```
┌─────────────────────────────────────────────────────────────┐
│  CONSENSUS FLOW: Adding a Voter                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Step 1: Validator 0 Proposes                               │
│  ┌────────────────────────────────────────────┐             │
│  │ Proposal: Add Alice                         │             │
│  │ - userId: "alice"                           │             │
│  │ - secret: 567                               │             │
│  │ - nullifierTrapdoor: 890                    │             │
│  │ - votes: [validator0]                       │             │
│  └────────────────────────────────────────────┘             │
│                      ↓                                       │
│  Step 2: Other Validators Vote                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Validator 1 │  │ Validator 2 │  │ Validator 3 │        │
│  │   APPROVE   │  │   APPROVE   │  │   REJECT    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│         │                │                 │                │
│         └────────────────┴─────────────────┘                │
│                      ↓                                       │
│  Step 3: Threshold Reached (3 votes ≥ threshold)           │
│  ┌────────────────────────────────────────────┐             │
│  │ Execute: Add Alice to all validators       │             │
│  │ - Validator 0: users["alice"] = Alice      │             │
│  │ - Validator 1: users["alice"] = Alice      │             │
│  │ - Validator 2: users["alice"] = Alice      │             │
│  └────────────────────────────────────────────┘             │
│                      ↓                                       │
│  Result: All validators have IDENTICAL state                │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 Block Production & Multi-Sig (Block Proposer Model)

```
┌──────────────────────────────────────────────────────────────┐
│  BLOCK PRODUCTION FLOW (Single Proposer + Multi-Sig)         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Step 1: Block Proposer Builds Block                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Validator 0 (Proposer):                                  │ │
│  │   users = {Alice, Bob, Charlie}                          │ │
│  │   merkleTree = MerkleTree(users)                         │ │
│  │   merkleRoot = tree.getRoot()                            │ │
│  │   → merkleRoot = 0x123abc...                             │ │
│  │                                                           │ │
│  │ Create BlockHeader:                                       │ │
│  │   blockHeight: 1                                         │ │
│  │   merkleRoot: 0x123abc...                                │ │
│  │   timestamp: 1700000000                                  │ │
│  │   parentHash: 0x000...                                   │ │
│  │   blockHash: 0xdef456...                                 │ │
│  │                                                           │ │
│  │ Sign the block:                                           │ │
│  │   headerHash = keccak256(header)                         │ │
│  │   ethSignedHash = prefixedHash(headerHash)               │ │
│  │   sig0 = ECDSA_sign(ethSignedHash, privKey0)            │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              ↓                                │
│  Step 2: Broadcast to Other Validators                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Proposer broadcasts BlockProposal:                       │ │
│  │   - BlockHeader                                           │ │
│  │   - Proposer's signature                                  │ │
│  │                                                           │ │
│  │ → Sent to: Validator 1, 2, 3, 4                         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              ↓                                │
│  Step 3: Validators Verify & Sign                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Each Validator Independently:                            │ │
│  │                                                           │ │
│  │ Validator 1:                                             │ │
│  │   1. Rebuild Merkle tree from own user data              │ │
│  │      merkleRoot_local = tree.getRoot()                   │ │
│  │   2. Compare: merkleRoot_local == header.merkleRoot     │ │
│  │      ✅ Match! State synchronized                        │ │
│  │   3. Verify proposer signature                           │ │
│  │      recoveredSigner = ecrecover(sig0)                   │ │
│  │      ✅ Valid proposer                                   │ │
│  │   4. Sign if valid                                        │ │
│  │      sig1 = ECDSA_sign(ethSignedHash, privKey1)         │ │
│  │                                                           │ │
│  │ Validator 2: (same process)                              │ │
│  │   → sig2 = ECDSA_sign(ethSignedHash, privKey2)          │ │
│  │                                                           │ │
│  │ Validator 3: (detects mismatch)                          │ │
│  │   merkleRoot_local = 0xDIFFERENT...                      │ │
│  │   ❌ REJECT - State not synchronized                     │ │
│  │   → No signature                                          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              ↓                                │
│  Step 4: Collect Signatures                                  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Proposer collects signatures:                            │ │
│  │   - sig0 (proposer's own)                                │ │
│  │   - sig1 (from Validator 1)                              │ │
│  │   - sig2 (from Validator 2)                              │ │
│  │                                                           │ │
│  │ Total: 3 signatures                                       │ │
│  │ Threshold: 3-of-5                                         │ │
│  │ → 3 ≥ 3 ✅ THRESHOLD REACHED                            │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              ↓                                │
│  Step 5: Finalize Block                                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Block {                                                  │ │
│  │   height: 1                                              │ │
│  │   stateRoot: 0x123abc...                                 │ │
│  │   signatures: [sig0, sig1, sig2]                         │ │
│  │   valid_signature_count: 3                               │ │
│  │ }                                                         │ │
│  │                                                           │ │
│  │ → Block added to all validators' local chains            │ │
│  │ → Broadcast to network                                    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  If Threshold NOT Reached:                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Only 2 signatures collected (< 3 threshold)              │ │
│  │ → Block REJECTED                                          │ │
│  │ → State desynchronization detected                        │ │
│  │ → Need to sync validators before next block              │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘

Key Advantages:
✅ Efficient: Only proposer builds block (not all validators)
✅ Validators verify independently (trustless)
✅ Threshold mechanism ensures majority agreement
✅ Automatic state sync detection
```

### 2. **Relayer Architecture**

```
┌────────────────────────────────────────────────────────────────┐
│  RELAYER: Bridge between Chain B and Chain A                   │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: Monitor Chain B                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Watch for new blocks on Chain B                          │  │
│  │ - Listen to BlockProduced events                          │  │
│  │ - Fetch block data (header + signatures)                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  Step 2: Collect Data                                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ BlockData {                                               │  │
│  │   header: {                                               │  │
│  │     blockHeight: 1                                        │  │
│  │     merkleRoot: 0x123abc... (as bytes32)                 │  │
│  │     timestamp: 1700000000                                 │  │
│  │     parentHash: 0x000...                                  │  │
│  │     blockHash: 0xdef456...                                │  │
│  │   },                                                       │  │
│  │   signatures: [sig0, sig1, sig2]                          │  │
│  │ }                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  Step 3: Submit to Chain A                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Call: Updater.submitHeader(header, signatures)           │  │
│  │                                                            │  │
│  │ Transaction on Chain A:                                    │  │
│  │ - Gas: ~500k                                               │  │
│  │ - Verifies multi-sig on-chain                             │  │
│  │ - Stores merkleRoot if valid                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│  Step 4: Confirmation                                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Wait for transaction confirmation                         │  │
│  │ - Check tx receipt                                         │  │
│  │ - Verify HeaderSubmitted event                            │  │
│  │ - Update relayer state                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Properties:                                                    │
│  - Trustless: Relayer cannot forge data (multi-sig verified)   │
│  - Permissionless: Anyone can run a relayer                    │
│  - Incentivized: Can charge fee for relaying                   │
└────────────────────────────────────────────────────────────────┘
```

### 3. **Updater Contract (Light Client)**

```solidity
contract Updater {
    // Validators (set at deployment)
    mapping(address => bool) public isOwner;
    uint256 public immutable threshold;
    uint256 public immutable ownerCount;

    // Verified state from Chain B
    mapping(uint256 => BlockHeader) public verifiedHeaders;
    mapping(uint256 => bytes32) public validRoots;

    function submitHeader(
        BlockHeader calldata header,
        bytes[] calldata signatures
    ) external {
        // 1. Validate block height (monotonic)
        require(header.blockHeight > latestBlockHeight);

        // 2. Hash header
        bytes32 headerHash = keccak256(abi.encodePacked(
            header.blockHeight,
            header.merkleRoot,
            header.timestamp,
            header.parentHash,
            header.blockHash
        ));

        // 3. Verify multi-sig
        bytes32 ethSignedHash = keccak256(
            abi.encodePacked("\x19Ethereum Signed Message:\n32", headerHash)
        );

        uint256 validSigs = 0;
        for (uint i = 0; i < signatures.length; i++) {
            address signer = ecrecover(ethSignedHash, signatures[i]);
            require(isOwner[signer], "Invalid signer");
            validSigs++;
        }

        require(validSigs >= threshold, "Not enough signatures");

        // 4. Store verified state
        verifiedHeaders[header.blockHeight] = header;
        validRoots[header.blockHeight] = header.merkleRoot;
        latestBlockHeight = header.blockHeight;
    }

    function isValidRoot(uint256 blockHeight, bytes32 root)
        external view returns (bool)
    {
        return validRoots[blockHeight] == root && root != bytes32(0);
    }
}
```

---

## 🔄 Luồng Hoạt Động End-to-End

### **Phase 1: Voter Registration (Chain B)**

```
┌─────────────────────────────────────────────────────────────────┐
│  1. VOTER REGISTRATION                                           │
└─────────────────────────────────────────────────────────────────┘

Time: T0
Actor: Validator 0
Action: Propose adding Alice

┌─────────────────────────────────────────────────┐
│ propose_add_user(                                │
│   userId: "alice",                               │
│   secret: 567,                                   │
│   nullifierTrapdoor: 890                         │
│ )                                                │
│                                                  │
│ → Proposal ID: "add-alice-1"                    │
│ → Votes: [validator0] (1/3)                     │
└─────────────────────────────────────────────────┘
                    ↓
Time: T1
Actors: Validator 1, 2
Action: Vote on proposal

┌─────────────────────────────────────────────────┐
│ vote_proposal("add-alice-1", validator1)         │
│ → Votes: [validator0, validator1] (2/3)         │
│                                                  │
│ vote_proposal("add-alice-1", validator2)         │
│ → Votes: [val0, val1, val2] (3/3) ✅           │
│ → THRESHOLD REACHED!                            │
│ → Execute: Add Alice to all validators          │
└─────────────────────────────────────────────────┘
                    ↓
Time: T2
Result: All validators synchronized

┌─────────────────────────────────────────────────┐
│ Validator 0: users = {Alice}                    │
│ Validator 1: users = {Alice}                    │
│ Validator 2: users = {Alice}                    │
│ Validator 3: users = {Alice}                    │
│ Validator 4: users = {Alice}                    │
│                                                  │
│ ✅ STATE SYNCHRONIZED                           │
└─────────────────────────────────────────────────┘
```

### **Phase 2: Block Production (Chain B)**

```
┌─────────────────────────────────────────────────────────────────┐
│  2. BLOCK PRODUCTION                                             │
└─────────────────────────────────────────────────────────────────┘

Time: T3
Action: Produce block

┌─────────────────────────────────────────────────┐
│ produce_block()                                  │
│                                                  │
│ Each Validator Calculates:                      │
│ 1. Build Merkle tree from users                 │
│    - Leaf = poseidonHash(secret)                │
│    - Parent = poseidonHash(left, right)         │
│ 2. merkleRoot = tree.getRoot()                  │
│    → 0x123abc...                                │
│                                                  │
│ 3. Create header                                │
│    - blockHeight: 1                             │
│    - merkleRoot: 0x123abc...                    │
│    - timestamp: 1700000000                      │
│                                                  │
│ 4. headerHash = keccak256(header)               │
│    → 0xdef456...                                │
│                                                  │
│ 5. Sign header                                   │
│    - ethSignedHash = prefixedHash(headerHash)   │
│    - signature = ECDSA.sign(ethSignedHash)      │
└─────────────────────────────────────────────────┘
                    ↓
Time: T4
Result: Block finalized

┌─────────────────────────────────────────────────┐
│ Block #1 {                                      │
│   height: 1                                     │
│   stateRoot: 0x123abc...                        │
│   signatures: [sig0, sig1, sig2]               │
│   validSignatures: 3 ≥ 3 ✅                    │
│ }                                                │
│                                                  │
│ → Block added to Chain B                        │
└─────────────────────────────────────────────────┘
```

### **Phase 3: Cross-Chain Relay**

```
┌─────────────────────────────────────────────────────────────────┐
│  3. CROSS-CHAIN RELAY                                            │
└─────────────────────────────────────────────────────────────────┘

Time: T5
Actor: Relayer
Action: Detect new block on Chain B

┌─────────────────────────────────────────────────┐
│ Relayer monitors Chain B:                       │
│ - Detects Block #1                              │
│ - Fetches block data                            │
│   * header                                       │
│   * signatures                                   │
└─────────────────────────────────────────────────┘
                    ↓
Time: T6
Action: Submit to Chain A

┌─────────────────────────────────────────────────┐
│ Relayer calls Updater.submitHeader():           │
│                                                  │
│ tx = updater.submitHeader(                      │
│   header: {                                      │
│     blockHeight: 1,                             │
│     merkleRoot: 0x123abc...,                    │
│     timestamp: 1700000000,                      │
│     parentHash: 0x000...,                       │
│     blockHash: 0xdef456...                      │
│   },                                             │
│   signatures: [sig0, sig1, sig2]                │
│ )                                                │
└─────────────────────────────────────────────────┘
                    ↓
Time: T7
Chain A: Updater contract verifies

┌─────────────────────────────────────────────────┐
│ Updater.submitHeader() executes:                │
│                                                  │
│ 1. Hash header                                   │
│    headerHash = keccak256(header)               │
│                                                  │
│ 2. Verify each signature                        │
│    For each sig:                                 │
│      signer = ecrecover(prefixedHash, sig)      │
│      require(isValidator(signer))               │
│                                                  │
│ 3. Check threshold                              │
│    require(validSigs >= 3) ✅                   │
│                                                  │
│ 4. Store merkleRoot                             │
│    validRoots[1] = 0x123abc...                  │
│                                                  │
│ emit HeaderSubmitted(1, 0x123abc...)            │
└─────────────────────────────────────────────────┘
                    ↓
Time: T8
Result: Chain A has merkleRoot from Chain B

┌─────────────────────────────────────────────────┐
│ Chain A State:                                   │
│ validRoots[1] = 0x123abc...                     │
│                                                  │
│ Now voters can prove membership in this root!   │
└─────────────────────────────────────────────────┘
```

### **Phase 4: Off-Chain ZK Proof Generation**

```
┌─────────────────────────────────────────────────────────────────┐
│  4. ZK PROOF GENERATION (Off-Chain)                              │
└─────────────────────────────────────────────────────────────────┘

Time: T9
Actor: Alice
Action: Generate ZK proof to vote

┌─────────────────────────────────────────────────┐
│ Alice's Private Data:                           │
│ - secret: 567                                   │
│ - nullifierTrapdoor: 890                        │
│ - Merkle proof from Chain B:                    │
│   * pathElements: [hash_bob, ...]              │
│   * pathIndices: [0, ...]                      │
│                                                  │
│ Alice's Public Inputs:                          │
│ - merkleRoot: 0x123abc... (from Chain A)       │
│ - electionId: 1                                 │
│ - candidateId: 2 (Alice votes for candidate 2) │
└─────────────────────────────────────────────────┘
                    ↓
Time: T10
Alice runs Circom circuit

┌─────────────────────────────────────────────────┐
│ Circuit Execution:                               │
│                                                  │
│ 1. Calculate leaf                                │
│    leaf = poseidonHash(567)                     │
│                                                  │
│ 2. Verify Merkle proof                          │
│    computedRoot = computeMerkle(                │
│      leaf, pathElements, pathIndices            │
│    )                                             │
│    assert(computedRoot == 0x123abc...) ✅       │
│                                                  │
│ 3. Calculate nullifier                          │
│    nullifierHash = poseidonHash(                │
│      secret: 567,                               │
│      nullifierTrapdoor: 890,                    │
│      electionId: 1                              │
│    )                                             │
│    → 0x789def...                                │
│                                                  │
│ 4. Generate Groth16 proof                       │
│    proof = {                                     │
│      pi_a: [x1, y1],                            │
│      pi_b: [[x2, y2], [x3, y3]],               │
│      pi_c: [x4, y4],                            │
│      publicSignals: [0x789def...]              │
│    }                                             │
└─────────────────────────────────────────────────┘
                    ↓
Time: T11
Result: Alice has valid ZK proof

┌─────────────────────────────────────────────────┐
│ Proof Properties:                                │
│ ✅ Proves Alice is in merkle tree               │
│ ✅ Without revealing her identity                │
│ ✅ nullifierHash prevents double voting          │
│ ✅ Links vote to specific election               │
└─────────────────────────────────────────────────┘
```

### **Phase 5: Vote Submission (Chain A)**

```
┌─────────────────────────────────────────────────────────────────┐
│  5. VOTE SUBMISSION                                              │
└─────────────────────────────────────────────────────────────────┘

Time: T12
Actor: Alice
Action: Submit vote to Chain A

┌─────────────────────────────────────────────────┐
│ Alice calls Voting.submitVote():                │
│                                                  │
│ voting.submitVote(                              │
│   proof: [pi_a, pi_b, pi_c],                   │
│   blockHeight: 1,                               │
│   electionId: 1,                                │
│   candidateId: 2                                │
│ )                                                │
└─────────────────────────────────────────────────┘
                    ↓
Time: T13
Chain A: Voting contract processes

┌─────────────────────────────────────────────────┐
│ Voting.submitVote() executes:                   │
│                                                  │
│ 1. Extract nullifierHash from proof             │
│    nullifierHash = proof.publicSignals[0]       │
│    → 0x789def...                                │
│                                                  │
│ 2. Check not double voting                      │
│    require(!nullifierHashes[0x789def...])       │
│    ✅ First time voting                         │
│                                                  │
│ 3. Get merkleRoot from Updater                  │
│    merkleRoot = updater.getRootAtHeight(1)      │
│    → 0x123abc...                                │
│    require(merkleRoot != 0) ✅                  │
│                                                  │
│ 4. Verify ZK proof                              │
│    bool valid = verifier.verifyProof(           │
│      proof, [nullifierHash]                     │
│    )                                             │
│    require(valid) ✅                            │
│                                                  │
│ 5. Record vote                                   │
│    nullifierHashes[0x789def...] = true          │
│    voteCounts[2]++  // Candidate 2              │
│                                                  │
│ emit VoteSubmitted(0x789def..., 2)              │
└─────────────────────────────────────────────────┘
                    ↓
Time: T14
Result: Vote recorded successfully

┌─────────────────────────────────────────────────┐
│ Chain A State After Vote:                       │
│ - nullifierHashes[0x789def...] = true           │
│ - voteCounts[2] = 1                             │
│                                                  │
│ ✅ Alice voted successfully                     │
│ ✅ Vote is anonymous (identity hidden)           │
│ ✅ Cannot vote again (nullifier recorded)        │
└─────────────────────────────────────────────────┘
```

---

## 🔒 Tính Bảo Mật

### 1. **Privacy (Ẩn danh)**

```
Attacker's View on Chain A:
┌────────────────────────────────────────┐
│ Transaction:                            │
│ - From: 0xabc... (Alice's wallet)      │
│ - To: Voting contract                   │
│ - Data: proof + nullifierHash          │
│                                         │
│ What attacker CANNOT know:             │
│ ❌ Alice's secret                       │
│ ❌ Alice's position in Merkle tree      │
│ ❌ Merkle proof path                    │
│ ❌ Which voter identity Alice has       │
│                                         │
│ What attacker CAN know:                 │
│ ✅ Someone voted                        │
│ ✅ Vote for candidate 2                 │
│ ✅ nullifierHash (but meaningless)      │
└────────────────────────────────────────┘
```

**Zero-Knowledge Property:**

-   Proof tiết lộ: "Tôi là voter hợp lệ trong merkleRoot"
-   Proof KHÔNG tiết lộ: "Tôi là Alice" hoặc vị trí trong tree

### 2. **Integrity (Chống vote trùng)**

```
Double Voting Attack:
┌────────────────────────────────────────┐
│ Alice tries to vote twice:             │
│                                         │
│ Vote 1:                                 │
│ - nullifierHash = H(secret, trap, elId)│
│ - nullifierHash = 0x789def...          │
│ - Recorded: nullifiers[0x789def...]=true│
│ ✅ Success                              │
│                                         │
│ Vote 2 (same secret, election):        │
│ - nullifierHash = 0x789def... (same!)  │
│ - Check: nullifiers[0x789def...]==true │
│ ❌ REJECTED: Already voted              │
└────────────────────────────────────────┘
```

**Nullifier Property:**

-   Unique per (voter, election) pair
-   Same nullifier → Same voter
-   Cannot vote twice in same election

### 3. **Soundness (Chống giả mạo)**

```
Forging Attack:
┌────────────────────────────────────────┐
│ Attacker (not in voter list) tries:   │
│                                         │
│ Option 1: Fake secret                  │
│ - Use random secret: 999               │
│ - leaf = poseidon(999)                 │
│ - Merkle verification fails ❌         │
│ → Proof generation fails               │
│                                         │
│ Option 2: Steal Alice's secret         │
│ - Need to know secret=567              │
│ - This is private, off-chain           │
│ - Infeasible without compromising Alice│
│                                         │
│ Option 3: Fake proof                   │
│ - Try to create valid proof without    │
│   knowing secret                        │
│ - Groth16 soundness: computationally   │
│   infeasible (relies on bilinear pairings)│
│ - Security: 128-bit                    │
│ → All attacks fail ❌                  │
└────────────────────────────────────────┘
```

### 4. **Cross-Chain Security**

```
Chain B Compromise Attack:
┌────────────────────────────────────────┐
│ Scenario: Attacker controls 2-of-5     │
│           validators (below threshold) │
│                                         │
│ Attack: Try to submit fake merkleRoot  │
│                                         │
│ Step 1: Create malicious block         │
│ - merkleRoot = 0xFAKE...               │
│ - Get signatures from 2 controlled vals│
│                                         │
│ Step 2: Submit to Chain A               │
│ - Call updater.submitHeader()          │
│ - Only 2 signatures                    │
│ - require(2 >= 3) → FAIL ❌            │
│                                         │
│ Result: Attack blocked by threshold    │
│                                         │
│ Required for attack: ≥3 validators     │
│ Byzantine Fault Tolerance: 2-of-5      │
└────────────────────────────────────────┘
```

---

## 📊 Performance & Costs

### Gas Costs (Chain A)

| Operation       | Gas Cost   | USD (@ $2000/ETH, 30 gwei) |
| --------------- | ---------- | -------------------------- |
| Deploy Updater  | ~2,000,000 | ~$120                      |
| Deploy Voting   | ~3,000,000 | ~$180                      |
| Deploy Verifier | ~1,500,000 | ~$90                       |
| submitHeader()  | ~500,000   | ~$30                       |
| submitVote()    | ~350,000   | ~$21                       |

### Proof Generation Time

| Step               | Time  | Hardware |
| ------------------ | ----- | -------- |
| Witness generation | ~0.1s | Laptop   |
| Proof generation   | ~2-5s | Laptop   |
| Proof verification | ~0.3s | On-chain |

### Scalability

-   **Chain B**: 100-1000 TPS (typical blockchain)
-   **Chain A**: 15-20 TPS (Ethereum)
-   **Bottleneck**: Chain A submitVote() calls
-   **Solution**: Batch voting or L2 rollups

---

## 🎯 Ưu Điểm & Hạn Chế

### Ưu Điểm

✅ **Privacy**: Bỏ phiếu hoàn toàn ẩn danh
✅ **Security**: Chống giả mạo, chống vote trùng
✅ **Verifiability**: Ai cũng verify được kết quả
✅ **Decentralization**: Không có trusted party
✅ **Cross-Chain**: Tận dụng security của 2 chains
✅ **Trustless Relay**: Relayer không thể cheat

### Hạn Chế

❌ **Gas Cost**: Đắt (~$21 per vote on Ethereum mainnet)
❌ **Proof Generation**: Cần device khá mạnh
❌ **Setup Ceremony**: Groth16 cần trusted setup
❌ **Circuit Complexity**: Khó debug, khó upgrade
❌ **Relayer Dependency**: Cần relayer hoạt động
❌ **Latency**: Cross-chain delay (minutes)

### Giải Pháp

💡 **Layer 2**: Deploy trên Arbitrum/Optimism → giảm gas
💡 **PLONK**: Thay Groth16 → không cần trusted setup
💡 **Recursive Proofs**: Batch multiple votes
💡 **Incentivize Relayers**: Phí relay + staking
💡 **Multiple Relayers**: Redundancy

---

## 🚀 Future Improvements

### 1. Vote Batching

```
Instead of: 1 vote = 1 proof = 1 tx
Upgrade to: N votes = 1 recursive proof = 1 tx
→ Giảm gas cost theo O(log N)
```

### 2. ZK Rollups

```
Move voting to L2 rollup
- Proof verification off-chain
- Only submit batch proof to L1
→ Giảm cost 100x
```

### 3. Multi-Chain Registry

```
Chain B → Sharded registry chains
- Each shard handles subset of voters
- Parallel processing
→ Tăng throughput
```

### 4. Decentralized Relayer Network

```
- Staking mechanism cho relayers
- Slash nếu submit sai data
- Reward cho relay đúng
→ Incentivized decentralization
```

---

## 📚 Tài Liệu Tham Khảo

-   **Circom**: https://docs.circom.io/
-   **Groth16**: https://eprint.iacr.org/2016/260.pdf
-   **Poseidon Hash**: https://eprint.iacr.org/2019/458.pdf
-   **Cross-Chain Bridge**: https://ethereum.org/en/developers/docs/bridges/
-   **Multi-Sig**: https://en.bitcoin.it/wiki/Multi-signature

---

**Document Version**: 1.0
**Last Updated**: 2025-11-16
**Author**: ZKP Voting System Team
