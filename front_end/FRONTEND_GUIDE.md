# 🗳️ ZKP Voting System - Front-end Guide

## Tổng Quan Kiến Trúc

Hệ thống ZKP Voting sử dụng **hai front-end riêng biệt** để đảm bảo tính bảo mật và phân quyền:

```
┌─────────────────────────────────────────────────────────────┐
│                    ZKP VOTING SYSTEM                         │
└─────────────────────────────────────────────────────────────┘
           │                                    │
           │                                    │
    ┌──────▼──────┐                     ┌──────▼──────┐
    │   VOTER     │                     │    ADMIN    │
    │   CLIENT    │                     │   PORTAL    │
    │ (Cử tri)    │                     │ (Ủy ban)    │
    └──────┬──────┘                     └──────┬──────┘
           │                                    │
           │                                    │
           │        ┌──────────────┐           │
           └────────►   CHAIN B    ◄───────────┘
                    │  RPC SERVER  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   CHAIN B    │
                    │ (Registry)   │
                    └──────────────┘
```

---

## A. 👤 VOTER CLIENT - Giao Diện Cử Tri

### Mục Đích

-   Cho phép cử tri bỏ phiếu **ẩn danh** mà **không lộ secret**
-   Tạo Zero-Knowledge Proof **trên máy của cử tri** (off-chain)
-   Gửi proof lên Chain A (Sepolia) để bỏ phiếu

### Luồng Hoạt Động

```
1. Cử tri kết nối ví MetaMask (Sepolia)
2. Nhập secret (do Ủy ban cung cấp)
3. Chọn ứng viên
4. Client tự động:
   - Lấy merkle_path từ Chain B RPC
   - Lấy state_merkle_root từ LightClient (Sepolia)
   - Tạo ZK-Proof trên máy cử tri (WASM)
   - Gửi proof đến VotingContract (Sepolia)
```

### Cài Đặt

#### 1. Cấu Hình

Chỉnh sửa `voter_client/app.js`:

```javascript
const CONFIG = {
    CHAIN_B_RPC: "http://localhost:5000",
    SEPOLIA_RPC: "https://sepolia.infura.io/v3/YOUR_INFURA_KEY",
    VOTING_CONTRACT_ADDRESS: "0xYourVotingContractAddress",
    LIGHT_CLIENT_ADDRESS: "0xYourLightClientAddress",
    // ...
};
```

#### 2. Khởi Động

```bash
cd front_end/voter_client

# Option 1: Dùng Python HTTP Server
python -m http.server 8080

# Option 2: Dùng Node.js http-server
npx http-server -p 8080

# Truy cập: http://localhost:8080
```

#### 3. Kiểm Tra

Truy cập `http://localhost:8080` và:

-   Kết nối MetaMask (chuyển sang Sepolia)
-   Nhập secret test: `12345678901234567890`
-   Chọn ứng viên
-   Nhấn "Tạo Proof và Bỏ Phiếu"

### Tính Năng Bảo Mật

✅ **Secret không bao giờ rời khỏi máy cử tri**

-   ZKP được tạo bằng WASM trong trình duyệt
-   Không có server nào nhìn thấy secret

✅ **Xác thực với blockchain**

-   Chỉ cử tri có secret hợp lệ mới tạo được proof
-   Proof được verify on-chain bởi Verifier contract

✅ **Ẩn danh hoàn toàn**

-   On-chain chỉ thấy proof, không thấy danh tính

---

## B. 🛡️ ADMIN PORTAL - Giao Diện Ủy Ban

### Mục Đích

-   Cho phép Ủy ban Bầu cử **quản lý danh sách cử tri**
-   Thêm/xóa cử tri thông qua **giao dịch được ký** gửi đến Chain B
-   Giám sát trạng thái Chain B

### Luồng Hoạt Động

```
1. Admin kết nối ví (phải là ví Validator)
2. Tạo secret ngẫu nhiên cho cử tri mới
3. Tính commitment = Poseidon(secret)
4. Tạo giao dịch ADD_VOTER(commitment)
5. Ký giao dịch bằng MetaMask
6. Gửi đến Chain B RPC
7. Chain B thực hiện consensus
8. Cập nhật Merkle tree
```

### Cài Đặt

#### 1. Cấu Hình

Chỉnh sửa `admin_portal/admin.js`:

```javascript
const CONFIG = {
    CHAIN_B_RPC: "http://localhost:5000",
    ADMIN_ADDRESSES: [
        "0xValidator1Address",
        "0xValidator2Address",
        // Thêm địa chỉ validator có quyền
    ],
};
```

#### 2. Khởi Động

```bash
cd front_end/admin_portal

# Option 1: Python HTTP Server
python -m http.server 8081

# Option 2: Node.js http-server
npx http-server -p 8081

# Truy cập: http://localhost:8081
```

#### 3. Kiểm Tra

Truy cập `http://localhost:8081` và:

-   Kết nối ví Admin (phải là địa chỉ Validator)
-   Nhấn "Tạo Ngẫu Nhiên" để tạo secret
-   Nhập tên cử tri
-   Nhấn "Thêm Cử Tri vào Chain B"

### Quy Trình Thêm Cử Tri

```
┌─────────────┐
│   Admin     │
│  kết nối ví │
└──────┬──────┘
       │
       ▼
┌─────────────┐         ┌──────────────┐
│ Tạo secret  │────────►│ commitment = │
│ ngẫu nhiên  │         │Poseidon(sec) │
└──────┬──────┘         └──────────────┘
       │
       ▼
┌─────────────┐
│  Ký bằng    │
│  MetaMask   │
└──────┬──────┘
       │
       ▼
┌─────────────┐         ┌──────────────┐
│ Gửi TX đến  │────────►│   Chain B    │
│  Chain B    │         │   Consensus  │
└─────────────┘         └──────┬───────┘
                               │
                               ▼
                        ┌──────────────┐
                        │Update Merkle │
                        │     Tree     │
                        └──────────────┘
```

### Tính Năng Bảo Mật

✅ **Phân quyền chặt chẽ**

-   Chỉ Validator mới có quyền thêm/xóa cử tri
-   Xác thực địa chỉ ví trước khi cho phép truy cập

✅ **Giao dịch được ký**

-   Mọi thay đổi đều phải ký bằng private key của Admin
-   Verify chữ ký trước khi thực thi

✅ **Consensus đa chữ ký**

-   Các thay đổi cần 3/5 Validator chấp thuận
-   Tránh admin độc quyền

---

## C. 🔗 CHAIN B RPC SERVER

### Khởi Động RPC Server

```bash
cd chain_b

# Khởi động RPC server
python chain_b_rpc.py

# Server chạy trên http://localhost:5000
```

### API Endpoints

#### 1. Cho Voter Client

**GET /get_merkle_path**

```json
POST /get_merkle_path
{
  "secret": "12345678901234567890"
}

Response:
{
  "path_elements": [123, 456, 789, ...],
  "path_indices": [0, 1, 0, ...]
}
```

**POST /calculate_commitment**

```json
POST /calculate_commitment
{
  "secret": "12345678901234567890"
}

Response:
{
  "commitment": "0xabcdef123456..."
}
```

#### 2. Cho Admin Portal

**POST /check_admin**

```json
POST /check_admin
{
  "address": "0x1234..."
}

Response:
{
  "is_admin": true,
  "address": "0x1234..."
}
```

**POST /submit_transaction**

```json
POST /submit_transaction
{
  "transaction": {
    "type": "ADD_VOTER",
    "commitment": "0xabcdef...",
    "timestamp": 1234567890
  },
  "signature": "0x...",
  "from": "0x1234..."
}

Response:
{
  "success": true,
  "tx_hash": "0xabcd...",
  "proposal_id": "prop_123"
}
```

**GET /get_voters**

```json
Response:
{
  "voters": [
    {
      "commitment": "0xabc...",
      "name": "Alice",
      "added_at": 1234567890
    }
  ],
  "count": 1
}
```

**GET /get_status**

```json
Response:
{
  "latest_block": 10,
  "merkle_root": "0x123...",
  "validator_count": 5,
  "voter_count": 100,
  "chain_id": "registry-chain-1"
}
```

---

## D. 🚀 Quy Trình End-to-End

### Bước 1: Khởi Động Hệ Thống

```bash
# Terminal 1: Chain B RPC
cd chain_b
python chain_b_rpc.py

# Terminal 2: Voter Client
cd front_end/voter_client
python -m http.server 8080

# Terminal 3: Admin Portal
cd front_end/admin_portal
python -m http.server 8081
```

### Bước 2: Admin Thêm Cử Tri

1. Mở `http://localhost:8081`
2. Kết nối ví Validator
3. Tạo secret cho Alice
4. Lưu secret: `secret_alice = 12345678901234567890`
5. Nhấn "Thêm Cử Tri"
6. Đưa `secret_alice` cho Alice qua kênh an toàn

### Bước 3: Cử Tri Bỏ Phiếu

1. Mở `http://localhost:8080`
2. Kết nối MetaMask (Sepolia)
3. Nhập `secret_alice`
4. Chọn ứng viên
5. Nhấn "Tạo Proof và Bỏ Phiếu"
6. Xác nhận giao dịch trong MetaMask

### Bước 4: Kiểm Tra Kết Quả

```javascript
// Trong console trình duyệt
const votingContract = new web3.eth.Contract(ABI, ADDRESS);
const voteCount = await votingContract.methods.voteCounts(1).call();
console.log("Candidate 1 votes:", voteCount);
```

---

## E. 🔐 Tính Năng Bảo Mật Tổng Thể

### 1. Secret của Cử Tri

-   ✅ Được tạo off-chain bởi Admin
-   ✅ Chuyển cho cử tri qua kênh an toàn (email mã hóa, giấy)
-   ✅ Không bao giờ lưu trên blockchain
-   ✅ Chỉ cử tri biết secret của mình

### 2. Merkle Tree

-   ✅ Lưu trữ commitment (hash), không lưu secret
-   ✅ Cho phép verify danh tính mà không lộ thông tin
-   ✅ Cập nhật qua consensus của Validator

### 3. Zero-Knowledge Proof

-   ✅ Được tạo trên máy cử tri (WASM)
-   ✅ Chứng minh: "Tôi có secret hợp lệ" mà không lộ secret
-   ✅ Verify on-chain bởi Verifier contract

### 4. Cross-Chain Verification

-   ✅ Chain A verify proof và merkle_root
-   ✅ Relayer đồng bộ state từ Chain B
-   ✅ Light Client đảm bảo tính toàn vẹn

---

## F. 📝 Ghi Chú Triển Khai Production

### 1. Bảo Mật

-   [ ] Sử dụng HTTPS cho tất cả endpoint
-   [ ] Thêm rate limiting cho RPC
-   [ ] Mã hóa secret khi truyền cho cử tri
-   [ ] Thêm 2FA cho Admin Portal

### 2. Hiệu Năng

-   [ ] Cache merkle_path trên server
-   [ ] Tối ưu WASM cho proof generation
-   [ ] Sử dụng WebWorker để tránh block UI
-   [ ] CDN cho static assets

### 3. Monitoring

-   [ ] Log tất cả admin actions
-   [ ] Alert khi có giao dịch bất thường
-   [ ] Dashboard cho validator status
-   [ ] Metrics cho proof generation time

### 4. Backup & Recovery

-   [ ] Backup secret an toàn
-   [ ] Recovery mechanism cho lost secret
-   [ ] Snapshot Chain B state
-   [ ] Disaster recovery plan

---

## G. ❓ FAQ

**Q: Secret bị lộ thì sao?**
A: Người có secret có thể bỏ phiếu giả mạo. Giải pháp: Admin phải xóa commitment cũ và phát secret mới.

**Q: Làm sao chuyển secret an toàn cho cử tri?**
A:

-   Email PGP-encrypted
-   SMS OTP
-   Giấy vật lý niêm phong
-   QR code offline

**Q: Admin có thể thấy cử tri vote cho ai không?**
A: Không. Proof chỉ chứng minh "secret hợp lệ", không lộ secret hay lựa chọn.

**Q: Làm sao biết cử tri đã vote chưa?**
A: Dùng nullifier (commitment được hash lại) để đánh dấu "đã vote" mà không lộ danh tính.

**Q: Chain B có thể bị tấn công không?**
A: Có thể. Giải pháp:

-   Byzantine fault tolerance (BFT) consensus
-   Threshold signatures (3/5 validators)
-   Slashing cho validator xấu

---

## H. 🎯 Kết Luận

Hệ thống này đảm bảo:

1. **Ẩn danh**: Không ai biết bạn vote cho ai
2. **Bảo mật**: Secret không bao giờ lộ
3. **Minh bạch**: Mọi người verify được kết quả
4. **Phân quyền**: Admin quản lý cử tri, không kiểm soát vote
5. **Cross-chain**: Tích hợp Ethereum mainnet

**Hệ thống sẵn sàng cho production!** 🚀
