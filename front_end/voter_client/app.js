import {buildPoseidon} from "https://esm.sh/circomlibjs@0.1.7";
// ✅ Dòng mới (Load trực tiếp từ mạng)
import {ethers} from "https://cdnjs.cloudflare.com/ajax/libs/ethers/5.7.2/ethers.esm.min.js";
// ==================== CONFIGURATION ====================
const CONFIG = {
    CHAIN_B_RPC: "http://127.0.0.1:5000",
    VOTING_CONTRACT_ADDRESS: "0x06f96CDe639ed441d67E4954Cb9D3834232dF2eA", // Replace after deployment
    LIGHT_CLIENT_ADDRESS: "0x191CAa18062a9f9D41314dbbe97A94850bc4b031", // Replace after deployment
    REQUIRED_NETWORK_ID: "11155111", // Sepolia
    CIRCUIT_WASM: "../../zkp_proof/voting_js/voting.wasm",
    CIRCUIT_ZKEY: "../../zkp_proof/voting_0001.zkey",
};

// Global Poseidon instance (initialized on load)
// Global Poseidon instance (initialized on load)
let poseidonInstance = null;
async function initPoseidon() {
    if (!poseidonInstance) {
        try {
            console.log("🔄 Đang khởi tạo Poseidon...");
            // Gọi hàm đã import ở trên
            poseidonInstance = await buildPoseidon();

            console.log("✅ Poseidon initialized via ESM");
        } catch (e) {
            console.error("Lỗi Poseidon:", e);
            if (typeof showError === "function")
                showError("Lỗi thư viện mật mã: " + e.message);
        }
    }
    return poseidonInstance;
}

// Hash function using Poseidon for single input (like poseidonHash1 in circuit)
function poseidonHash1(data) {
    if (!poseidonInstance) {
        throw new Error("Poseidon not initialized. Call initPoseidon() first.");
    }
    const F = poseidonInstance.F;
    return F.toObject(poseidonInstance([BigInt(data)]));
}

// Hash function using Poseidon for two inputs (like poseidonHash2 in circuit)
function poseidonHash2(left, right) {
    if (!poseidonInstance) {
        throw new Error("Poseidon not initialized. Call initPoseidon() first.");
    }
    const F = poseidonInstance.F;
    return F.toObject(poseidonInstance([BigInt(left), BigInt(right)]));
}

// ==================== VOTING CONTRACT ABI ====================
const VOTING_ABI = [
    {
        inputs: [
            {internalType: "address", name: "_verifier", type: "address"},
            {internalType: "address", name: "_updater", type: "address"},
            {internalType: "uint256", name: "_electionId", type: "uint256"},
            {internalType: "uint256", name: "_numCandidates", type: "uint256"},
        ],
        stateMutability: "nonpayable",
        type: "constructor",
    },
    {inputs: [], name: "AlreadyVoted", type: "error"},
    {inputs: [], name: "InvalidMerkleRoot", type: "error"},
    {inputs: [], name: "InvalidProof", type: "error"},
    {inputs: [], name: "Unauthorized", type: "error"},
    {inputs: [], name: "VotingHasEnded", type: "error"},
    {
        anonymous: false,
        inputs: [
            {
                indexed: false,
                internalType: "uint256",
                name: "newElectionId",
                type: "uint256",
            },
        ],
        name: "ElectionUpdated",
        type: "event",
    },
    {
        anonymous: false,
        inputs: [
            {
                indexed: false,
                internalType: "uint256",
                name: "newNumCandidates",
                type: "uint256",
            },
        ],
        name: "NumCandidatesUpdated",
        type: "event",
    },
    {
        anonymous: false,
        inputs: [
            {
                indexed: true,
                internalType: "address",
                name: "voter",
                type: "address",
            },
            {
                indexed: false,
                internalType: "bytes32",
                name: "commitment",
                type: "bytes32",
            },
            {
                indexed: false,
                internalType: "uint256",
                name: "nullifierHash",
                type: "uint256",
            },
        ],
        name: "VoteSubmitted",
        type: "event",
    },
    {
        anonymous: false,
        inputs: [
            {
                indexed: false,
                internalType: "uint256",
                name: "totalVotes",
                type: "uint256",
            },
        ],
        name: "VotingEnded",
        type: "event",
    },
    {anonymous: false, inputs: [], name: "VotingReopened", type: "event"},
    {
        anonymous: false,
        inputs: [
            {
                indexed: false,
                internalType: "uint256",
                name: "winnerId",
                type: "uint256",
            },
            {
                indexed: false,
                internalType: "uint256",
                name: "winnerVotes",
                type: "uint256",
            },
        ],
        name: "WinnerDeclared",
        type: "event",
    },
    {
        inputs: [{internalType: "uint256", name: "", type: "uint256"}],
        name: "candidateVotes",
        outputs: [{internalType: "uint256", name: "", type: "uint256"}],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "electionId",
        outputs: [{internalType: "uint256", name: "", type: "uint256"}],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "getAllVotes",
        outputs: [{internalType: "uint256[]", name: "", type: "uint256[]"}],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [
            {internalType: "uint256", name: "candidateId", type: "uint256"},
        ],
        name: "getCandidateVotes",
        outputs: [{internalType: "uint256", name: "", type: "uint256"}],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "getElectionInfo",
        outputs: [
            {internalType: "uint256", name: "_electionId", type: "uint256"},
            {internalType: "bytes32", name: "_merkleRoot", type: "bytes32"},
            {internalType: "uint256", name: "_numCandidates", type: "uint256"},
            {internalType: "uint256", name: "_totalVotes", type: "uint256"},
            {internalType: "bool", name: "_votingEnded", type: "bool"},
        ],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "getLatestBlockHeight",
        outputs: [{internalType: "uint256", name: "", type: "uint256"}],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "getMerkleRoot",
        outputs: [{internalType: "bytes32", name: "", type: "bytes32"}],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "getTotalVotes",
        outputs: [{internalType: "uint256", name: "", type: "uint256"}],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "getUpdater",
        outputs: [{internalType: "address", name: "", type: "address"}],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "getVerifier",
        outputs: [{internalType: "address", name: "", type: "address"}],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [
            {internalType: "uint256", name: "nullifierHash", type: "uint256"},
        ],
        name: "hasVoted",
        outputs: [{internalType: "bool", name: "", type: "bool"}],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "numCandidates",
        outputs: [{internalType: "uint256", name: "", type: "uint256"}],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "owner",
        outputs: [{internalType: "address", name: "", type: "address"}],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [
            {
                internalType: "uint256",
                name: "_newNumCandidates",
                type: "uint256",
            },
        ],
        name: "setNumCandidates",
        outputs: [],
        stateMutability: "nonpayable",
        type: "function",
    },
    {
        inputs: [
            {internalType: "uint256[2]", name: "a", type: "uint256[2]"},
            {internalType: "uint256[2][2]", name: "b", type: "uint256[2][2]"},
            {internalType: "uint256[2]", name: "c", type: "uint256[2]"},
            {
                internalType: "uint256[4]",
                name: "publicSignals",
                type: "uint256[4]",
            },
            {internalType: "uint256", name: "candidateId", type: "uint256"},
        ],
        name: "submitVoteLatest",
        outputs: [],
        stateMutability: "nonpayable",
        type: "function",
    },
    {
        inputs: [],
        name: "totalVotes",
        outputs: [{internalType: "uint256", name: "", type: "uint256"}],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [{internalType: "bytes32", name: "_newRoot", type: "bytes32"}],
        name: "updateMerkleRoot",
        outputs: [],
        stateMutability: "nonpayable",
        type: "function",
    },
    {
        inputs: [],
        name: "updater",
        outputs: [
            {internalType: "contract IUpdater", name: "", type: "address"},
        ],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "verifier",
        outputs: [
            {
                internalType: "contract Groth16Verifier",
                name: "",
                type: "address",
            },
        ],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "votingEnded",
        outputs: [{internalType: "bool", name: "", type: "bool"}],
        stateMutability: "view",
        type: "function",
    },
];
// ==================== STATE ====================
let web3;
let userAccount;
let selectedCandidate = null;
let voterSecret = null;
let nullifierTrapdoor = null;
let contract;
let signer;

// ==================== INITIALIZATION ====================
document.addEventListener("DOMContentLoaded", () => {
    initializeApp();
});

async function initializeApp() {
    // Initialize Poseidon first
    await initPoseidon();

    // Check MetaMask availability
    if (typeof window.ethereum === "undefined") {
        showError(
            "MetaMask chưa được cài đặt! Vui lòng cài đặt MetaMask để tiếp tục."
        );
        return;
    }

    // Event Listeners
    document
        .getElementById("connect-wallet-btn")
        .addEventListener("click", connectWallet);
    document.querySelectorAll(".voter-secret").forEach((input) => {
        input.addEventListener("input", validateSecret);
    });
    document
        .getElementById("submit-vote-btn")
        .addEventListener("click", submitVote);

    // Listen to account changes
    window.ethereum.on("accountsChanged", handleAccountsChanged);
    window.ethereum.on("chainChanged", () => window.location.reload());
}

// ==================== WALLET CONNECTION ====================
async function connectWallet() {
    try {
        showProgress("Đang kết nối MetaMask...", 10);

        web3 = new Web3(window.ethereum);
        const accounts = await window.ethereum.request({
            method: "eth_requestAccounts",
        });
        userAccount = accounts[0];

        // Check network
        const networkId = await web3.eth.net.getId();
        if (networkId.toString() !== CONFIG.REQUIRED_NETWORK_ID) {
            showError("Vui lòng chuyển sang mạng Sepolia trong MetaMask!");
            return;
        }

        signer = new ethers.providers.Web3Provider(window.ethereum).getSigner();
        contract = new ethers.Contract(
            CONFIG.VOTING_CONTRACT_ADDRESS,
            VOTING_ABI,
            signer
        );

        // Update UI Status Bar
        document.getElementById(
            "wallet-address"
        ).textContent = `${userAccount.substring(
            0,
            6
        )}...${userAccount.substring(38)}`;
        document.getElementById("network-name").textContent = "Sepolia";

        showProgress("Kết nối thành công!", 100);

        // --- SỬA TẠI ĐÂY ---

        // CÁCH 1: Chỉ ẩn nút bấm (Giữ lại tiêu đề bước 1)
        // document.getElementById("connect-wallet-btn").style.display = "none";

        // CÁCH 2: Ẩn toàn bộ khung Bước 1 (Khuyên dùng để giao diện gọn hơn)
        document.getElementById("step-connect").style.display = "none";

        // -------------------

        // Show next steps
        document.getElementById("step-secret").style.display = "block";

        // Nếu bạn muốn hiện luôn bước bầu cử thì để dòng này,
        // còn nếu muốn nhập xong secret mới hiện bầu cử thì ẩn dòng này đi
        document.getElementById("step-vote").style.display = "block";

        // Update Stepper UI (Nếu bạn dùng giao diện mới tôi gửi ở bước trước)
        updateStepper(2);

        // Load candidates
        await loadCandidates();
        // Kiểm tra xem bầu cử đã kết thúc chưa?
        await checkElectionStatus();

        // Lắng nghe sự kiện người chiến thắng (Real-time)
        listenForWinner();
    } catch (error) {
        console.error("Wallet connection error:", error);
        showError("Không thể kết nối ví: " + error.message);
    }
}

function updateStepper(stepNumber) {
    // Xóa class active cũ
    document.querySelectorAll(".stepper-item").forEach((item) => {
        item.classList.remove("active");
    });

    // Thêm class active cho các bước đã qua
    document.querySelectorAll(".stepper-item").forEach((item) => {
        if (parseInt(item.dataset.step) <= stepNumber) {
            item.classList.add("active");
        }
    });
}

function handleAccountsChanged(accounts) {
    if (accounts.length === 0) {
        // Người dùng ngắt kết nối ví hoàn toàn
        showError("Vui lòng kết nối ví MetaMask!");

        // Hiện lại nút kết nối / Bước 1
        document.getElementById("step-connect").style.display = "block";
        document.getElementById("connect-wallet-btn").style.display =
            "inline-block"; // hoặc "block"

        // Ẩn các bước sau
        document.getElementById("step-secret").style.display = "none";
        document.getElementById("step-vote").style.display = "none";

        // Reset thông tin
        document.getElementById("wallet-address").textContent = "Chưa kết nối";
    } else if (accounts[0] !== userAccount) {
        // Người dùng đổi sang ví khác -> Reload lại trang cho sạch state
        userAccount = accounts[0];
        window.location.reload();
    }
}

// ==================== SECRET HANDLING ====================
function toggleSecretVisibility() {
    const input = document.getElementById("voter-secret");
    const btn = document.getElementById("toggle-secret-btn");

    if (input.type === "password") {
        input.type = "text";
        btn.textContent = "🙈 Ẩn";
    } else {
        input.type = "password";
        btn.textContent = "👁️ Hiện";
    }
}

function validateSecret() {
    const input1 = document.getElementById("voter-secret-1");
    const input2 = document.getElementById("voter-secret-2");
    const statusDiv = document.getElementById("secret-status");

    if (!input1 || !input2) return;

    const s1 = input1.value.trim();
    const s2 = input2.value.trim();

    if (!s1 && !s2) {
        if (statusDiv) statusDiv.innerHTML = "";
        return;
    }

    try {
        // Basic check
        const b1 = BigInt(s1);
        const b2 = BigInt(s2);

        voterSecret = b1.toString();
        nullifierTrapdoor = b2.toString();
        console.log("Voter Secret:", voterSecret);
        console.log("Nullifier Trapdoor:", nullifierTrapdoor);

        if (statusDiv) {
            statusDiv.innerHTML =
                '<span style="color:#10b981">✅ Hợp lệ</span>';
            statusDiv.className = "status-message success";
        }
    } catch (e) {
        if (statusDiv) {
            statusDiv.innerHTML =
                '<span style="color:#ef4444">❌ Không hợp lệ</span>';
            statusDiv.className = "status-message error";
        }
    }
}

// ==================== CANDIDATE SELECTION ====================
async function loadCandidates() {
    const candidateList = document.getElementById("candidate-list");

    // Mock candidates (in production, fetch from contract)
    const candidates = [
        {id: 1, name: "Nguyễn Văn A", party: "Đảng A"},
        {id: 2, name: "Trần Thị B", party: "Đảng B"},
        {id: 3, name: "Lê Văn C", party: "Đảng C"},
        {id: 4, name: "Phạm Thị D", party: "Đảng D"},
        {id: 5, name: "Hoàng Văn E", party: "Đảng E"},
    ];

    candidateList.innerHTML = candidates
        .map(
            (candidate) => `
        <div class="candidate-card" data-candidate-id="${candidate.id}" onclick="selectCandidate(${candidate.id}, '${candidate.name}')">
            <h3>${candidate.name}</h3>
            <p>${candidate.party}</p>
        </div>
    `
        )
        .join("");
}

window.selectCandidate = function (candidateId, candidateName) {
    selectedCandidate = candidateId;
    console.log("Selected Candidate ID:", selectedCandidate);
    // Update UI
    document.querySelectorAll(".candidate-card").forEach((card) => {
        card.classList.remove("selected");
    });
    document
        .querySelector(`[data-candidate-id="${candidateId}"]`)
        .classList.add("selected");
    document.getElementById("selected-candidate-name").textContent =
        candidateName;

    // Show submit section
    document.getElementById("step-submit").style.display = "block";
};

// ==================== PROOF GENERATION & SUBMISSION ====================
async function submitVote() {
    console.log("Submitting vote...");
    console.log(voterSecret);
    console.log(nullifierTrapdoor);
    try {
        // Validation
        if (!voterSecret || !nullifierTrapdoor) {
            showError("Vui lòng nhập đầy đủ mã bí mật và nullifier trapdoor!");
            return;
        }
        if (!selectedCandidate) {
            showError("Vui lòng chọn ứng viên!");
            return;
        }

        showProgress("Bắt đầu quá trình bỏ phiếu...", 10);

        // Step 1: Calculate commitment from secret
        showProgress("🔑 Đang tính commitment...", 20);
        const myCommitment = await calculateCommitmentFromSecret(voterSecret);
        console.log("My commitment:", myCommitment.toString());
        console.log(
            "My commitment (hex):",
            "0x" + myCommitment.toString(16).padStart(64, "0")
        );

        // Step 2: Get merkle proof from Chain B (server calculates path for security)
        showProgress("🌳 Đang lấy Merkle Proof từ Chain B...", 30);
        const proofData = await getMerkleProofFromChainB(myCommitment);
        console.log("Merkle proof data:", proofData);

        const pathElements = proofData.path_elements;
        const pathIndices = proofData.path_indices;

        // Step 3: Get election info from contract
        showProgress("🔗 Đang lấy thông tin bầu cử từ contract...", 40);
        const votingContract = new web3.eth.Contract(
            VOTING_ABI,
            CONFIG.VOTING_CONTRACT_ADDRESS
        );
        const electionInfo = await votingContract.methods
            .getElectionInfo()
            .call();
        const electionId = electionInfo._electionId;
        const numCandidates = parseInt(electionInfo._numCandidates);

        // Step 5: Build vote array (one-hot encoded)
        const NUM_CANDIDATES_CIRCUIT = 100;
        const randomness = BigInt(123456); // Example randomness
        const voteIndex = selectedCandidate - 1; // Bỏ phiếu cho ứng viên được chọn (0-indexed)

        // Tạo mảng phiếu bầu (one-hot encoded)
        const votes = Array(NUM_CANDIDATES_CIRCUIT).fill(BigInt(0));
        if (voteIndex < NUM_CANDIDATES_CIRCUIT) {
            votes[voteIndex] = BigInt(1);
        }

        // Băm nối tiếp (Chained Hashing) - Giống hệt logic trong Circom
        let currentHashState = randomness;
        for (let k = 0; k < NUM_CANDIDATES_CIRCUIT; k++) {
            currentHashState = poseidonHash2(currentHashState, votes[k]);
        }
        const commitment = currentHashState;

        // Step 7: Generate ZK-Proof locally
        showProgress(
            "🧮 Đang tạo Zero-Knowledge Proof (có thể mất 30s-1 phút)...",
            50
        );

        const circuitInput = {
            // Private inputs
            secret: voterSecret.toString(),
            nullifierTrapdoor: nullifierTrapdoor.toString(),
            vote: votes,
            randomness: randomness.toString(),
            pathElements: pathElements,
            pathIndices: pathIndices,

            // Public inputs
            electionId: electionId.toString(),
            merkleRoot: proofData.merkle_root,
            commitment: commitment.toString(),
        };

        console.log("Circuit input:", circuitInput);

        const {proof, publicSignals} = await generateZKProof(circuitInput);

        // Step 8: Submit proof to VotingContract
        showProgress("📤 Đang gửi proof lên Sepolia...", 80);
        const txHash = await submitProofToContract(
            proof,
            publicSignals,
            selectedCandidate - 1
        );

        // Success
        showProgress("✅ Bỏ phiếu thành công!", 100);
        showSuccess(`Giao dịch đã được xác nhận! TX Hash: ${txHash}`);
    } catch (error) {
        console.error("🔴 Chi tiết lỗi gốc:", error); // Log toàn bộ để debug
        showError("Lỗi:" + error);
    }
}

// Get merkle proof for a specific commitment from Chain B (server calculates path)
async function getMerkleProofFromChainB(commitment) {
    const response = await fetch(`${CONFIG.CHAIN_B_RPC}/get_merkle_proof`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({commitment: commitment.toString()}),
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
            errorData.error || "Không thể lấy merkle proof từ Chain B"
        );
    }
    return await response.json();
}

// Get public merkle root from Chain B (for verification)
async function getMerkleRootFromChainB() {
    const response = await fetch(`${CONFIG.CHAIN_B_RPC}/get_merkle_root`, {
        method: "GET",
        headers: {"Content-Type": "application/json"},
    });

    if (!response.ok) {
        throw new Error("Không thể lấy merkle root từ Chain B");
    }
    return await response.json();
}

// Calculate commitment from secret (Poseidon single input hash - matches calcInput.js)
async function calculateCommitmentFromSecret(secret) {
    const poseidon = await initPoseidon();
    const F = poseidon.F;
    const commitment = F.toObject(poseidon([BigInt(secret)]));

    // Debug log
    console.log("🔑 Secret:", secret);
    console.log("📝 Calculated commitment:", "0x" + commitment.toString(16));

    return commitment;
}

// ==================== REMOVED: Client-side merkle tree building ====================
// These functions are no longer needed - Chain B RPC now calculates merkle path server-side
// This improves security by:
// 1. Not exposing full voter registry to clients
// 2. Reducing client bandwidth and computation
// 3. Preventing DoS attacks via large tree downloads
// 4. Centralizing merkle logic in one trusted location

// Get state merkle root from LightClient contract
async function getStateMerkleRootFromSepolia() {
    const lightClientContract = new web3.eth.Contract(
        LIGHT_CLIENT_ABI,
        CONFIG.LIGHT_CLIENT_ADDRESS
    );

    const root = await lightClientContract.methods.merkleRoot().call();
    return root.toString();
}

// Generate ZK-Proof using snarkjs
async function generateZKProof(input) {
    try {
        const {proof, publicSignals} = await snarkjs.groth16.fullProve(
            input,
            CONFIG.CIRCUIT_WASM,
            CONFIG.CIRCUIT_ZKEY
        );

        // Format proof for Solidity
        const solidityProof = {
            a: [proof.pi_a[0], proof.pi_a[1]],
            b: [
                [proof.pi_b[0][1], proof.pi_b[0][0]],
                [proof.pi_b[1][1], proof.pi_b[1][0]],
            ],
            c: [proof.pi_c[0], proof.pi_c[1]],
        };

        return {proof: solidityProof, publicSignals};
    } catch (error) {
        console.error("ZK Proof generation error:", error);
        throw new Error("Không thể tạo ZK-Proof: " + error.message);
    }
}

// Submit proof to VotingContract (with candidateId)
async function submitProofToContract(proof, publicSignals, candidateId) {
    const votingContract = new web3.eth.Contract(
        VOTING_ABI,
        CONFIG.VOTING_CONTRACT_ADDRESS
    );

    const tx = await votingContract.methods
        .submitVoteLatest(proof.a, proof.b, proof.c, publicSignals, candidateId)
        .send({
            from: userAccount,
            gas: 5000000,
        });

    return tx.transactionHash;
}

async function checkElectionStatus() {
    try {
        const electionInfo = await contract.getElectionInfo();
        const isEnded = electionInfo._votingEnded;
        const totalVotes = parseInt(electionInfo._totalVotes);
        const numCandidates = parseInt(electionInfo._numCandidates);

        console.log(
            `Trạng thái: ${totalVotes}/${numCandidates} phiếu. Ended: ${isEnded}`
        );

        if (isEnded || totalVotes >= numCandidates) {
            // Nếu đã kết thúc, hiển thị người chiến thắng
            await showWinnerScreen();
        }
    } catch (error) {
        console.error("Lỗi kiểm tra trạng thái:", error);
    }
}

function listenForWinner() {
    contract.on("WinnerDeclared", (winnerId, winnerVotes) => {
        console.log("🎉 Winner Declared Event:", winnerId, winnerVotes);
        showWinnerScreen(winnerId, winnerVotes);
    });
}

// --- HÀM MỚI: Hiển thị màn hình chiến thắng ---
async function showWinnerScreen(winnerId = null, winnerVotes = null) {
    // Ẩn tất cả các bước khác
    document.getElementById("step-connect").style.display = "none";
    document.getElementById("step-secret").style.display = "none";
    document.getElementById("step-vote").style.display = "none";
    document.getElementById("step-submit").style.display = "none";
    document.querySelector(".stepper-wrapper").style.display = "none"; // Ẩn thanh tiến trình

    // Hiện màn hình chiến thắng
    const winnerSection = document.getElementById("step-winner");
    winnerSection.style.display = "block";
    winnerSection.classList.add("active-section");

    // Nếu chưa có thông tin winner (do gọi từ checkStatus), phải fetch lại
    if (winnerId === null) {
        try {
            // Gọi hàm getWinner từ contract (nếu có public view)
            // Hoặc tính toán thủ công từ getCandidateVotes
            // Ở đây giả sử ta tính toán lại thủ công cho chắc ăn:
            const candidatesList = [
                {id: 1, name: "Nguyễn Văn A"},
                {id: 2, name: "Trần Thị B"},
                {id: 3, name: "Lê Văn C"},
                {id: 4, name: "Phạm Thị D"},
                {id: 5, name: "Hoàng Văn E"},
            ];

            let maxVotes = 0;
            let winningCandidate = candidatesList[0];

            for (let i = 0; i < candidatesList.length; i++) {
                // Candidate ID trong contract là index 0-based
                const votes = await contract.getCandidateVotes(i);
                const voteCount = parseInt(votes);

                if (voteCount > maxVotes) {
                    maxVotes = voteCount;
                    winningCandidate = candidatesList[i];
                }
            }

            document.getElementById("winner-name").textContent =
                winningCandidate.name;
            document.getElementById("winner-votes-count").textContent =
                maxVotes;
        } catch (e) {
            console.error("Lỗi lấy thông tin winner:", e);
        }
    } else {
        // Nếu có thông tin từ Event
        // Lưu ý: winnerId từ Event là 0-based index
        const candidatesList = [
            "Nguyễn Văn A",
            "Trần Thị B",
            "Lê Văn C",
            "Phạm Thị D",
            "Hoàng Văn E",
        ];
        const name = candidatesList[winnerId] || "Unknown Candidate";

        document.getElementById("winner-name").textContent = name;
        document.getElementById("winner-votes-count").textContent =
            winnerVotes.toString();
    }
}

// ==================== UI HELPERS ====================
function showProgress(message, percent) {
    const progressContainer = document.getElementById("proof-progress");
    const progressFill = document.getElementById("progress-fill");
    const progressText = document.getElementById("progress-text");

    progressContainer.style.display = "block";
    progressFill.style.width = percent + "%";
    progressText.textContent = message;
}

function showSuccess(message) {
    const resultDiv = document.getElementById("result-message");
    resultDiv.className = "result-message success";
    resultDiv.innerHTML = `✅ ${message}`;
}

function showError(message) {
    const resultDiv = document.getElementById("result-message");
    resultDiv.className = "result-message error";
    resultDiv.innerHTML = `❌ ${message}`;
}
