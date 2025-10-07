# 🗳️ ZKP Voting System

<div align="center">

![Solidity](https://img.shields.io/badge/Solidity-^0.8.0-363636?logo=solidity)
![Circom](https://img.shields.io/badge/Circom-2.0.0-purple)
![Node.js](https://img.shields.io/badge/Node.js-18+-green?logo=node.js)

**Privacy-preserving voting system using Zero-Knowledge Proofs on Ethereum**

[Demo](#-demo) • [Setup](#-setup) • [Usage](#-usage)

</div>

## 🌟 Features

-   **🔒 Private Voting**: Zero-knowledge proofs keep votes secret
-   **🚫 No Double Voting**: Nullifier system prevents duplicate votes
-   **✅ Verifiable**: Cryptographic proof ensures vote integrity
-   **⚡ Fast**: Groth16 proofs verify in milliseconds

## 🎮 Demo

**Live Contract**: [`0x8945A98c13228D70C323A9dF051Ee785008fcE17`](https://sepolia.etherscan.io/address/0x8945a98c13228d70c323a9df051ee785008fce17)

```bash
git clone https://github.com/b1endong/ZKP_voting_system.git
cd ZKP_voting_system && npm install
cd ScriptDemo && node DemoScript.js
```

## ⚡ Setup

### Prerequisites

-   Node.js 18+, Foundry, Circom

### Quick Start

```bash
# Install dependencies
npm install
npm install -g snarkjs circom_runtime

# Setup environment
cp .env.example .env  # Add your RPC URL and private key

# Compile circuit (optional - already compiled)
cd zkp_proof
circom circuit/voting.circom --r1cs --wasm --sym

# Generate input and run demo
cd input && node calcInput.js
cd ../../ScriptDemo && node DemoScript.js
```

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
```

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
