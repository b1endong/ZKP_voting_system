// ==================== CONFIGURATION ====================
const CONFIG = {
    CHAIN_B_RPC: "http://127.0.0.1:5000",
    ADMIN_ADDRESSES: ["0xD55B67EaF6B7C11C813aaa077467a889B58c17A4"],
};

// ==================== STATE ====================
let web3;
let adminAccount;
let isAuthenticated = false;

// ==================== INITIALIZATION ====================
document.addEventListener("DOMContentLoaded", () => {
    initializeApp();
});

function initializeApp() {
    // Check Web3 availability
    if (typeof window.ethereum === "undefined") {
        alert("MetaMask chưa được cài đặt!");
        return;
    }

    // Event Listeners
    document
        .getElementById("connect-admin-btn")
        .addEventListener("click", connectAdmin);
    document
        .getElementById("generate-secret-btn")
        .addEventListener("click", generateRandomSecret);
    document
        .getElementById("voter-secret-input")
        .addEventListener("input", updateCommitment);
    document
        .getElementById("add-voter-btn")
        .addEventListener("click", addVoter);
    document
        .getElementById("remove-voter-btn")
        .addEventListener("click", removeVoter);
    document
        .getElementById("refresh-list-btn")
        .addEventListener("click", loadVoterList);
    document
        .getElementById("produce-block-btn")
        .addEventListener("click", produceBlock);

    // Listen to account changes
    window.ethereum.on("accountsChanged", handleAccountsChanged);

    // Auto-check RPC status on page load
    checkRPCStatus();

    // Load danh sách cử tri ngay lập tức (chế độ view-only)
    loadVoterList();
}

async function checkRPCStatus() {
    try {
        const response = await fetch(`${CONFIG.CHAIN_B_RPC}/health`, {
            method: "GET",
            signal: AbortSignal.timeout(3000),
        });

        if (response.ok) {
            const data = await response.json();
            document.getElementById(
                "chain-b-status"
            ).textContent = `✅ Kết nối (Block #${data.blockHeight})`;

            // Cập nhật số liệu block mới nhất
            document.getElementById("latest-block").textContent =
                "#" + data.blockHeight;
        } else {
            document.getElementById("chain-b-status").textContent =
                "❌ RPC Error";
        }
    } catch (error) {
        console.error("RPC status check failed:", error);
        document.getElementById("chain-b-status").textContent =
            "❌ Không thể kết nối";
    }
}

// ==================== AUTHENTICATION ====================
async function connectAdmin() {
    const btn = document.getElementById("connect-admin-btn");
    const originalText = btn.textContent;

    try {
        // Show loading state
        btn.textContent = "Đang kết nối...";
        btn.disabled = true;

        web3 = new Web3(window.ethereum);
        const accounts = await window.ethereum.request({
            method: "eth_requestAccounts",
        });
        adminAccount = accounts[0];

        // Check if account is authorized admin
        const isAdmin = await checkAdminPermission(adminAccount);

        if (!isAdmin) {
            alert(
                "❌ Địa chỉ này không có quyền Admin! Vui lòng dùng ví được ủy quyền."
            );
            btn.textContent = originalText;
            btn.disabled = false;
            return;
        }

        isAuthenticated = true;

        // Cập nhật nút bấm thành địa chỉ ví
        btn.textContent = `🟢 ${adminAccount.substring(
            0,
            6
        )}...${adminAccount.substring(38)}`;
        btn.classList.replace("btn-primary", "btn-success"); // Đổi màu nút thành xanh lá

        // Load data
        await Promise.all([loadVoterList(), loadChainStatus()]);
    } catch (error) {
        console.error("Admin authentication error:", error);
        alert("❌ Lỗi xác thực: " + error.message);
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function checkAdminPermission(address) {
    try {
        // Call Chain B RPC to check if address is admin/validator
        const response = await fetch(`${CONFIG.CHAIN_B_RPC}/check_admin`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({address}),
        });

        if (!response.ok) {
            // Fallback: check against local config
            return CONFIG.ADMIN_ADDRESSES.map((a) => a.toLowerCase()).includes(
                address.toLowerCase()
            );
        }

        const data = await response.json();
        return data.is_admin;
    } catch (error) {
        console.warn("Admin check failed, using local config:", error);
        return CONFIG.ADMIN_ADDRESSES.map((a) => a.toLowerCase()).includes(
            address.toLowerCase()
        );
    }
}

function handleAccountsChanged(accounts) {
    if (accounts.length === 0 || accounts[0] !== adminAccount) {
        location.reload();
    }
}

// ==================== SECRET & COMMITMENT GENERATION ====================
function generateRandomSecret() {
    const randomBytes = new Uint8Array(32);
    crypto.getRandomValues(randomBytes);

    let secret = 0n;
    for (let i = 0; i < 32; i++) {
        secret = (secret << 8n) | BigInt(randomBytes[i]);
    }

    const FIELD_SIZE = BigInt(
        "21888242871839275222246405745257275088548364400416034343698204186575808495617"
    );
    secret = secret % FIELD_SIZE;

    document.getElementById("voter-secret-input").value = secret.toString();
    updateCommitment();
}

async function updateCommitment() {
    const secretInput = document
        .getElementById("voter-secret-input")
        .value.trim();
    const commitmentDisplay = document.getElementById("commitment-display");

    if (!secretInput) {
        commitmentDisplay.value = "";
        return;
    }

    try {
        const response = await fetch(
            `${CONFIG.CHAIN_B_RPC}/calculate_commitment`,
            {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({secret: secretInput}),
            }
        );

        if (!response.ok) {
            throw new Error("Không thể tính commitment");
        }

        const data = await response.json();
        commitmentDisplay.value = data.commitment;
    } catch (error) {
        console.error("Commitment calculation error:", error);
        commitmentDisplay.value = "Error: " + error.message;
    }
}

// ==================== VOTER MANAGEMENT ====================
async function addVoter() {
    if (!isAuthenticated) {
        alert("Vui lòng kết nối ví Admin trước!");
        return;
    }

    try {
        const name = document.getElementById("voter-name").value.trim();
        const secret = document
            .getElementById("voter-secret-input")
            .value.trim();
        const commitment = document
            .getElementById("commitment-display")
            .value.trim();

        if (!secret || !commitment) {
            showMessage(
                "add-voter-result",
                "error",
                "Vui lòng nhập hoặc tạo secret!"
            );
            return;
        }

        showMessage(
            "add-voter-result",
            "info",
            "⏳ Đang tạo proposal thêm cử tri..."
        );

        const txData = {
            type: "ADD_VOTER",
            commitment: commitment,
            metadata: {name: name || "Unknown"},
            timestamp: Date.now(),
        };
        console.log("Add Voter TX Data:", txData);

        const signature = await signTransaction(txData);

        const response = await fetch(
            `${CONFIG.CHAIN_B_RPC}/submit_transaction`,
            {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    transaction: txData,
                    signature: signature,
                    from: adminAccount,
                }),
            }
        );

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || "Giao dịch thất bại");
        }

        const result = await response.json();

        showMessage(
            "add-voter-result",
            "success",
            `✅ Thêm cử tri thành công!\nTX Hash: ${result.tx_hash}\n⚠️ Lưu lại secret: ${secret}`
        );

        await loadVoterList();

        document.getElementById("voter-name").value = "";
        document.getElementById("voter-secret-input").value = "";
        document.getElementById("commitment-display").value = "";
    } catch (error) {
        console.error("Add voter error:", error);
        showMessage("add-voter-result", "error", "❌ Lỗi: " + error.message);
    }
}

async function removeVoter() {
    if (!isAuthenticated) {
        alert("Vui lòng kết nối ví Admin trước!");
        return;
    }

    try {
        const commitment = document
            .getElementById("remove-commitment")
            .value.trim();

        if (!commitment) {
            showMessage(
                "remove-voter-result",
                "error",
                "Vui lòng nhập commitment!"
            );
            return;
        }

        if (!confirm("Bạn có chắc muốn xóa cử tri này?")) {
            return;
        }

        showMessage(
            "remove-voter-result",
            "info",
            "⏳ Đang tạo proposal xóa cử tri..."
        );

        const txData = {
            type: "REMOVE_VOTER",
            commitment: commitment,
            timestamp: Date.now(),
        };

        const signature = await signTransaction(txData);

        const response = await fetch(
            `${CONFIG.CHAIN_B_RPC}/submit_transaction`,
            {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    transaction: txData,
                    signature: signature,
                    from: adminAccount,
                }),
            }
        );

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || "Giao dịch thất bại");
        }

        const result = await response.json();

        showMessage(
            "remove-voter-result",
            "success",
            `✅ Xóa cử tri thành công!\nTX Hash: ${result.tx_hash}`
        );

        await loadVoterList();
        document.getElementById("remove-commitment").value = "";
    } catch (error) {
        console.error("Remove voter error:", error);
        showMessage("remove-voter-result", "error", "❌ Lỗi: " + error.message);
    }
}

// ==================== DATA LOADING ====================
async function loadVoterList() {
    try {
        const container = document.getElementById("voter-list-container");
        // Không hiển thị "Đang tải" nếu đã có dữ liệu để tránh nhấp nháy
        if (
            container.innerHTML.includes("empty-state") ||
            container.innerHTML === ""
        ) {
            container.innerHTML =
                '<p class="loading">Đang tải danh sách cử tri...</p>';
        }

        const response = await fetch(`${CONFIG.CHAIN_B_RPC}/get_voters`);

        if (!response.ok) {
            throw new Error("Không thể tải danh sách cử tri");
        }

        const data = await response.json();
        const voters = data.voters || [];

        document.getElementById("voter-count").textContent = voters.length;

        if (voters.length === 0) {
            container.innerHTML = `<div class="empty-state"><span>📭</span><p>Chưa có dữ liệu</p></div>`;
            return;
        }

        const table = document.createElement("table");
        table.innerHTML = `
            <thead>
                <tr>
                    <th>#</th>
                    <th>Tên</th>
                    <th>Commitment</th>
                    <th>Ngày Thêm</th>
                </tr>
            </thead>
            <tbody>
                ${voters
                    .map(
                        (voter, index) => `
                    <tr>
                        <td>${index + 1}</td>
                        <td>${voter.name || "N/A"}</td>
                        <td class="code-text" style="font-size: 0.8rem; color: var(--primary);">${voter.commitment.substring(
                            0,
                            20
                        )}...</td>
                        <td>${new Date(voter.added_at).toLocaleString(
                            "vi-VN"
                        )}</td>
                    </tr>
                `
                    )
                    .join("")}
            </tbody>
        `;

        container.innerHTML = "";
        container.appendChild(table);
    } catch (error) {
        console.error("Load voter list error:", error);
        // Chỉ hiện lỗi nếu không có dữ liệu cũ
    }
}

async function loadChainStatus() {
    try {
        const response = await fetch(`${CONFIG.CHAIN_B_RPC}/get_status`);
        if (response.ok) {
            const data = await response.json();
            document.getElementById("latest-block").textContent =
                "#" + (data.latest_block || "0");
            document.getElementById("merkle-root").textContent =
                (data.merkle_root || "0x0").substring(0, 20) + "...";
            document.getElementById("validator-count").textContent =
                data.validator_count || "0";

            // Nếu đã xác thực thì hiện trạng thái kết nối
            if (isAuthenticated) {
                document.getElementById("chain-b-status").textContent =
                    "✅ Đã kết nối";
            }
        }
    } catch (error) {
        console.error("Load chain status error:", error);
    }
}

// ==================== BLOCK PRODUCTION ====================
async function produceBlock() {
    if (!isAuthenticated) {
        alert("Vui lòng kết nối ví Admin trước!");
        return;
    }

    try {
        const btn = document.getElementById("produce-block-btn");
        btn.disabled = true;
        btn.textContent = "⏳ Đang tạo block...";

        showMessage(
            "produce-block-result",
            "info",
            "Đang gửi yêu cầu tạo block..."
        );

        const response = await fetch(`${CONFIG.CHAIN_B_RPC}/produce_block`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({from: adminAccount}),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Không thể tạo block");
        }

        showMessage(
            "produce-block-result",
            "success",
            `✅ Block #${
                data.block_height
            } đã được tạo thành công!\nMerkle Root: ${data.merkle_root.substring(
                0,
                20
            )}...`
        );

        await loadChainStatus();
        await loadVoterList();
    } catch (error) {
        console.error("Produce block error:", error);
        showMessage("produce-block-result", "error", `❌ ${error.message}`);
    } finally {
        const btn = document.getElementById("produce-block-btn");
        btn.disabled = false;
        btn.textContent = "Xác nhận & Tạo Block";
    }
}

async function signTransaction(txData) {
    try {
        const message = JSON.stringify(txData);
        const signature = await web3.eth.personal.sign(
            message,
            adminAccount,
            ""
        );
        return signature;
    } catch (error) {
        console.error("Transaction signing error:", error);
        throw new Error("Không thể ký giao dịch: " + error.message);
    }
}

function showMessage(elementId, type, message) {
    const element = document.getElementById(elementId);
    element.className = `message ${type} show`;
    element.textContent = message;
    if (type === "success") {
        setTimeout(() => {
            element.classList.remove("show");
        }, 5000);
    }
}
