// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

contract Updater {
    /*//////////////////////////////////////////////////////////////
                            TYPE DEFINITIONS
    //////////////////////////////////////////////////////////////*/

    // Block header từ chain B
    struct BlockHeader {
        uint256 blockHeight;
        bytes32 merkleRoot;
        uint256 timestamp;
        bytes32 parentHash;
        bytes32 blockHash;
    }

    /*//////////////////////////////////////////////////////////////
                            STATE VARIABLES
    //////////////////////////////////////////////////////////////*/

    // Mảng các validators
    mapping(address => bool) public isOwner;
    address[] public owners;

    // Số chữ ký cần thiết để xác nhận header
    uint256 public immutable threshold;

    // Tổng số validators (N trong M-of-N)
    uint256 public immutable ownerCount;

    // Bản ghi các header đã được xác nhận
    mapping(uint256 => BlockHeader) public verifiedHeaders;
    mapping(uint256 => bytes32) public validRoots;

    // Trạng thái đã được xác nhận mới nhất
    uint256 public latestBlockHeight;
    bytes32 public latestValidRoot;

    /*//////////////////////////////////////////////////////////////
                                EVENTS
    //////////////////////////////////////////////////////////////*/

    event HeaderSubmitted(
        uint256 indexed blockHeight,
        bytes32 indexed merkleRoot,
        bytes32 blockHash,
        uint256 validSignatures,
        address indexed relayer
    );

    event OwnerAdded(address indexed owner);
    event StateReset(uint256 resetToHeight, bytes32 genesisRoot);

    /*//////////////////////////////////////////////////////////////
                                ERRORS
    //////////////////////////////////////////////////////////////*/

    error InvalidBlockHeight();
    error InvalidParentHash();
    error InvalidTimestamp();
    error NotEnoughSignatures(uint256 provided, uint256 required);
    error InvalidSignature(uint256 index);
    error NotAnOwner(address signer);
    error DuplicateSignature(address signer);
    error InvalidThreshold();
    error ZeroAddress();

    /*//////////////////////////////////////////////////////////////
                            CONSTRUCTOR
    //////////////////////////////////////////////////////////////*/

    constructor(
        address[] memory _owners,
        uint256 _threshold,
        bytes32 _genesisMerkleRoot
    ) {
        if (_owners.length == 0) revert ZeroAddress();
        if (_threshold == 0 || _threshold > _owners.length)
            revert InvalidThreshold();

        // Khởi tạo các validators
        for (uint256 i = 0; i < _owners.length; i++) {
            address owner = _owners[i];
            if (owner == address(0)) revert ZeroAddress();
            if (isOwner[owner]) revert DuplicateSignature(owner);

            isOwner[owner] = true;
            owners.push(owner);

            emit OwnerAdded(owner);
        }

        threshold = _threshold;
        ownerCount = _owners.length;

        BlockHeader memory genesis;
        genesis.blockHeight = 0;
        genesis.merkleRoot = _genesisMerkleRoot;
        genesis.timestamp = 0;
        genesis.parentHash = bytes32(0);
        // Hash giả lập cho genesis (hoặc bạn có thể tính đúng nếu muốn)
        genesis.blockHash = keccak256(
            abi.encodePacked(
                uint256(0),
                _genesisMerkleRoot,
                uint256(0),
                bytes32(0)
            )
        );

        verifiedHeaders[0] = genesis;
        validRoots[0] = _genesisMerkleRoot;

        // Thiết lập trạng thái hiện tại là Block 0
        latestBlockHeight = 0;
        latestValidRoot = _genesisMerkleRoot;
    }

    /*//////////////////////////////////////////////////////////////
                             ADMIN FUNCTION
    //////////////////////////////////////////////////////////////*/

    function resetState() external {
        // Quay về Block 0 (Genesis)
        latestBlockHeight = 0;
        latestValidRoot = validRoots[0]; // Lấy lại Root của Genesis

        emit StateReset(0, latestValidRoot);
    }

    /*//////////////////////////////////////////////////////////////
                        HEADER SUBMISSION
    //////////////////////////////////////////////////////////////*/

    function submitHeader(
        BlockHeader calldata _header,
        bytes[] calldata signatures
    ) external {
        // 1. Kiểm tra độ cao block
        if (_header.blockHeight != latestBlockHeight + 1) {
            revert InvalidBlockHeight();
        }

        // 4. Recreate header hash
        bytes32 headerHash = _hashHeader(_header);

        // 5. Verify multi-sig (NEW LOGIC)
        _verifyMultiSig(headerHash, signatures);

        // 6. Store verified header
        verifiedHeaders[_header.blockHeight] = _header;
        validRoots[_header.blockHeight] = _header.merkleRoot;
        latestBlockHeight = _header.blockHeight;
        latestValidRoot = _header.merkleRoot;

        emit HeaderSubmitted(
            _header.blockHeight,
            _header.merkleRoot,
            _header.blockHash,
            signatures.length,
            msg.sender
        );
    }

    /*//////////////////////////////////////////////////////////////
                    MULTI-SIG VERIFICATION
    //////////////////////////////////////////////////////////////*/

    function _verifyMultiSig(
        bytes32 headerHash,
        bytes[] calldata signatures
    ) internal view {
        // Check minimum signature count
        if (signatures.length < threshold) {
            revert NotEnoughSignatures(signatures.length, threshold);
        }

        // Prepare Ethereum signed message hash
        bytes32 ethSignedHash = _getEthSignedMessageHash(headerHash);

        uint256 validCount = 0;

        // Verify each signature
        for (uint256 i = 0; i < signatures.length; i++) {
            // Recover signer from signature
            address signer = _recoverSigner(ethSignedHash, signatures[i]);

            // Check if signer is an owner
            if (!isOwner[signer]) {
                revert NotAnOwner(signer);
            }
            validCount++;
        }

        // Final threshold check
        if (validCount < threshold) {
            revert NotEnoughSignatures(validCount, threshold);
        }
    }

    function _hashHeader(
        BlockHeader calldata _header
    ) internal pure returns (bytes32) {
        return
            keccak256(
                abi.encodePacked(
                    _header.blockHeight,
                    _header.merkleRoot,
                    _header.timestamp,
                    _header.parentHash,
                    _header.blockHash
                )
            );
    }

    function _getEthSignedMessageHash(
        bytes32 messageHash
    ) internal pure returns (bytes32) {
        return
            keccak256(
                abi.encodePacked(
                    "\x19Ethereum Signed Message:\n32",
                    messageHash
                )
            );
    }

    function _recoverSigner(
        bytes32 ethSignedHash,
        bytes calldata signature
    ) internal pure returns (address) {
        require(signature.length == 65, "Invalid signature length");

        bytes32 r;
        bytes32 s;
        uint8 v;

        assembly {
            // First 32 bytes, after length prefix
            r := calldataload(signature.offset)
            // Second 32 bytes
            s := calldataload(add(signature.offset, 32))
            // Final byte
            v := byte(0, calldataload(add(signature.offset, 64)))
        }

        // Handle legacy v values
        if (v < 27) {
            v += 27;
        }

        require(v == 27 || v == 28, "Invalid v value");

        return ecrecover(ethSignedHash, v, r, s);
    }

    /*//////////////////////////////////////////////////////////////
                        ROOT VERIFICATION
    //////////////////////////////////////////////////////////////*/

    function isValidRoot(
        uint256 blockHeight,
        bytes32 merkleRoot
    ) external view returns (bool) {
        return
            validRoots[blockHeight] == merkleRoot && merkleRoot != bytes32(0);
    }

    function getRootAtHeight(
        uint256 blockHeight
    ) external view returns (bytes32) {
        return validRoots[blockHeight];
    }

    function getLatestRoot() external view returns (bytes32) {
        return latestValidRoot;
    }

    function getHeader(
        uint256 blockHeight
    ) external view returns (BlockHeader memory) {
        return verifiedHeaders[blockHeight];
    }

    /*//////////////////////////////////////////////////////////////
                        UTILITY FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    function getOwners() external view returns (address[] memory) {
        return owners;
    }

    function getConfig()
        external
        view
        returns (
            uint256 _threshold,
            uint256 _ownerCount,
            address[] memory _owners
        )
    {
        return (threshold, ownerCount, owners);
    }

    function checkIsOwner(address addr) external view returns (bool) {
        return isOwner[addr];
    }
}
