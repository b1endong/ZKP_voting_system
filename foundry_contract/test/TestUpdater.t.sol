// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import {Test, console} from "forge-std/Test.sol";
import {Updater} from "../src/Updater.sol";

/**
 * @title TestUpdater - Comprehensive tests with real Chain B data
 * @dev Chain B configuration: 5 validators, 3-of-5 threshold
 * Real merkle roots from Chain B with 4 users (alice, bob, charlie, dave)
 */
contract TestUpdater is Test {
    Updater public updater;

    address[] public validators;
    uint256[] public validatorPrivateKeys;
    uint256 public constant THRESHOLD = 3;

    // Real merkle roots from Chain B (in decimal)
    uint256 constant MERKLE_ROOT_BLOCK_1 =
        21123581264201458397189026598520511993018501003573368930253957488882163792310;
    uint256 constant MERKLE_ROOT_BLOCK_2 =
        4852784827717076318987031111413621451416327848463524312121183444525856951971;
    uint256 constant MERKLE_ROOT_BLOCK_3 =
        15442732266491406221157360034314941243457684092452001027844635192935244611954;

    function setUp() public {
        // Create 5 validators
        for (uint256 i = 1; i <= 5; i++) {
            uint256 pk = uint256(keccak256(abi.encodePacked("validator", i)));
            validatorPrivateKeys.push(pk);
            validators.push(vm.addr(pk));
        }

        updater = new Updater(validators, THRESHOLD);
    }

    /*//////////////////////////////////////////////////////////////
                        HELPER FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    function createBlockHeader(
        uint256 blockHeight,
        uint256 merkleRoot,
        uint256 timestamp,
        bytes32 parentHash
    ) internal pure returns (Updater.BlockHeader memory) {
        bytes32 blockHash = keccak256(
            abi.encodePacked(blockHeight, merkleRoot, timestamp, parentHash)
        );

        return
            Updater.BlockHeader({
                blockHeight: blockHeight,
                merkleRoot: bytes32(merkleRoot),
                timestamp: timestamp,
                parentHash: parentHash,
                blockHash: blockHash
            });
    }

    function signHeader(
        Updater.BlockHeader memory header,
        uint256[] memory privateKeys
    ) internal pure returns (bytes[] memory) {
        bytes[] memory signatures = new bytes[](privateKeys.length);

        bytes32 messageHash = keccak256(
            abi.encodePacked(
                header.blockHeight,
                header.merkleRoot,
                header.timestamp,
                header.parentHash,
                header.blockHash
            )
        );

        bytes32 ethSignedHash = keccak256(
            abi.encodePacked("\x19Ethereum Signed Message:\n32", messageHash)
        );

        for (uint256 i = 0; i < privateKeys.length; i++) {
            (uint8 v, bytes32 r, bytes32 s) = vm.sign(
                privateKeys[i],
                ethSignedHash
            );
            signatures[i] = abi.encodePacked(r, s, v);
        }

        return signatures;
    }

    /*//////////////////////////////////////////////////////////////
                        BASIC TESTS
    //////////////////////////////////////////////////////////////*/

    function test_Deployment() public view {
        assertEq(updater.threshold(), THRESHOLD);
        assertEq(updater.ownerCount(), validators.length);
        assertEq(updater.latestBlockHeight(), 0);

        for (uint256 i = 0; i < validators.length; i++) {
            assertTrue(updater.isOwner(validators[i]));
        }
    }

    /*//////////////////////////////////////////////////////////////
                    SINGLE BLOCK SUBMISSION TESTS
    //////////////////////////////////////////////////////////////*/

    function test_SubmitBlock1_WithThresholdSignatures() public {
        Updater.BlockHeader memory header = createBlockHeader({
            blockHeight: 1,
            merkleRoot: MERKLE_ROOT_BLOCK_1,
            timestamp: block.timestamp,
            parentHash: bytes32(0)
        });

        // 3 validators sign (exactly threshold)
        uint256[] memory signerKeys = new uint256[](3);
        signerKeys[0] = validatorPrivateKeys[0];
        signerKeys[1] = validatorPrivateKeys[1];
        signerKeys[2] = validatorPrivateKeys[2];

        bytes[] memory signatures = signHeader(header, signerKeys);

        vm.expectEmit(true, true, false, true);
        emit Updater.HeaderSubmitted(
            header.blockHeight,
            header.merkleRoot,
            header.blockHash,
            3,
            address(this)
        );

        updater.submitHeader(header, signatures);

        assertEq(updater.latestBlockHeight(), 1);
        assertEq(updater.getLatestRoot(), header.merkleRoot);
        assertTrue(updater.isValidRoot(1, header.merkleRoot));
    }

    function test_SubmitBlock1_WithAllSignatures() public {
        Updater.BlockHeader memory header = createBlockHeader({
            blockHeight: 1,
            merkleRoot: MERKLE_ROOT_BLOCK_1,
            timestamp: block.timestamp,
            parentHash: bytes32(0)
        });

        // All 5 validators sign
        bytes[] memory signatures = signHeader(header, validatorPrivateKeys);

        updater.submitHeader(header, signatures);

        assertEq(updater.latestBlockHeight(), 1);
        assertTrue(updater.isValidRoot(1, header.merkleRoot));
    }

    /*//////////////////////////////////////////////////////////////
                    MULTIPLE BLOCKS TESTS
    //////////////////////////////////////////////////////////////*/

    function test_SubmitThreeBlocksSequentially() public {
        uint256[] memory signerKeys = new uint256[](3);
        signerKeys[0] = validatorPrivateKeys[0];
        signerKeys[1] = validatorPrivateKeys[1];
        signerKeys[2] = validatorPrivateKeys[2];

        // Block 1
        Updater.BlockHeader memory header1 = createBlockHeader({
            blockHeight: 1,
            merkleRoot: MERKLE_ROOT_BLOCK_1,
            timestamp: block.timestamp,
            parentHash: bytes32(0)
        });
        updater.submitHeader(header1, signHeader(header1, signerKeys));

        // Block 2
        Updater.BlockHeader memory header2 = createBlockHeader({
            blockHeight: 2,
            merkleRoot: MERKLE_ROOT_BLOCK_2,
            timestamp: block.timestamp + 10,
            parentHash: header1.blockHash
        });
        updater.submitHeader(header2, signHeader(header2, signerKeys));

        // Block 3
        Updater.BlockHeader memory header3 = createBlockHeader({
            blockHeight: 3,
            merkleRoot: MERKLE_ROOT_BLOCK_3,
            timestamp: block.timestamp + 20,
            parentHash: header2.blockHash
        });
        updater.submitHeader(header3, signHeader(header3, signerKeys));

        // Verify all blocks
        assertEq(updater.latestBlockHeight(), 3);
        assertEq(updater.getLatestRoot(), header3.merkleRoot);
        assertTrue(updater.isValidRoot(1, header1.merkleRoot));
        assertTrue(updater.isValidRoot(2, header2.merkleRoot));
        assertTrue(updater.isValidRoot(3, header3.merkleRoot));

        console.log("Block 1 merkle root:", uint256(header1.merkleRoot));
        console.log("Block 2 merkle root:", uint256(header2.merkleRoot));
        console.log("Block 3 merkle root:", uint256(header3.merkleRoot));
    }

    /*//////////////////////////////////////////////////////////////
                        ERROR CASE TESTS
    //////////////////////////////////////////////////////////////*/

    function test_RevertWhen_InsufficientSignatures() public {
        Updater.BlockHeader memory header = createBlockHeader({
            blockHeight: 1,
            merkleRoot: MERKLE_ROOT_BLOCK_1,
            timestamp: block.timestamp,
            parentHash: bytes32(0)
        });

        // Only 2 signatures (less than threshold)
        uint256[] memory signerKeys = new uint256[](2);
        signerKeys[0] = validatorPrivateKeys[0];
        signerKeys[1] = validatorPrivateKeys[1];

        bytes[] memory signatures = signHeader(header, signerKeys);

        vm.expectRevert(
            abi.encodeWithSelector(
                Updater.NotEnoughSignatures.selector,
                2,
                THRESHOLD
            )
        );
        updater.submitHeader(header, signatures);
    }

    function test_RevertWhen_InvalidSignatures() public {
        Updater.BlockHeader memory header = createBlockHeader({
            blockHeight: 1,
            merkleRoot: MERKLE_ROOT_BLOCK_1,
            timestamp: block.timestamp,
            parentHash: bytes32(0)
        });

        // Create signatures with non-validator keys
        uint256[] memory invalidKeys = new uint256[](3);
        invalidKeys[0] = uint256(keccak256("invalid1"));
        invalidKeys[1] = uint256(keccak256("invalid2"));
        invalidKeys[2] = uint256(keccak256("invalid3"));

        bytes[] memory signatures = signHeader(header, invalidKeys);

        vm.expectRevert();
        updater.submitHeader(header, signatures);
    }

    function test_RevertWhen_DuplicateBlock() public {
        Updater.BlockHeader memory header = createBlockHeader({
            blockHeight: 1,
            merkleRoot: MERKLE_ROOT_BLOCK_1,
            timestamp: block.timestamp,
            parentHash: bytes32(0)
        });

        uint256[] memory signerKeys = new uint256[](3);
        signerKeys[0] = validatorPrivateKeys[0];
        signerKeys[1] = validatorPrivateKeys[1];
        signerKeys[2] = validatorPrivateKeys[2];

        bytes[] memory signatures = signHeader(header, signerKeys);

        // Submit first time
        updater.submitHeader(header, signatures);

        // Submit again - should revert
        vm.expectRevert();
        updater.submitHeader(header, signatures);
    }

    function test_RevertWhen_EmptySignatures() public {
        Updater.BlockHeader memory header = createBlockHeader({
            blockHeight: 1,
            merkleRoot: MERKLE_ROOT_BLOCK_1,
            timestamp: block.timestamp,
            parentHash: bytes32(0)
        });

        bytes[] memory emptySignatures = new bytes[](0);

        vm.expectRevert();
        updater.submitHeader(header, emptySignatures);
    }

    /*//////////////////////////////////////////////////////////////
                    QUERY FUNCTION TESTS
    //////////////////////////////////////////////////////////////*/

    function test_GetVerifiedHeader() public {
        Updater.BlockHeader memory header = createBlockHeader({
            blockHeight: 1,
            merkleRoot: MERKLE_ROOT_BLOCK_1,
            timestamp: block.timestamp,
            parentHash: bytes32(0)
        });

        uint256[] memory signerKeys = new uint256[](3);
        signerKeys[0] = validatorPrivateKeys[0];
        signerKeys[1] = validatorPrivateKeys[1];
        signerKeys[2] = validatorPrivateKeys[2];

        updater.submitHeader(header, signHeader(header, signerKeys));

        Updater.BlockHeader memory retrieved = updater.getHeader(1);

        assertEq(retrieved.blockHeight, header.blockHeight);
        assertEq(retrieved.merkleRoot, header.merkleRoot);
        assertEq(retrieved.timestamp, header.timestamp);
        assertEq(retrieved.parentHash, header.parentHash);
        assertEq(retrieved.blockHash, header.blockHash);
    }

    function test_GetNonExistentBlock_ReturnsZero() public view {
        Updater.BlockHeader memory retrieved = updater.getHeader(999);
        assertEq(retrieved.blockHeight, 0);
        assertEq(retrieved.merkleRoot, bytes32(0));
    }

    function test_IsValidRoot_MultipleBlocks() public {
        uint256[] memory signerKeys = new uint256[](3);
        signerKeys[0] = validatorPrivateKeys[0];
        signerKeys[1] = validatorPrivateKeys[1];
        signerKeys[2] = validatorPrivateKeys[2];

        Updater.BlockHeader memory header1 = createBlockHeader({
            blockHeight: 1,
            merkleRoot: MERKLE_ROOT_BLOCK_1,
            timestamp: block.timestamp,
            parentHash: bytes32(0)
        });
        updater.submitHeader(header1, signHeader(header1, signerKeys));

        Updater.BlockHeader memory header2 = createBlockHeader({
            blockHeight: 2,
            merkleRoot: MERKLE_ROOT_BLOCK_2,
            timestamp: block.timestamp + 10,
            parentHash: header1.blockHash
        });
        updater.submitHeader(header2, signHeader(header2, signerKeys));

        // Check validity
        assertTrue(updater.isValidRoot(1, header1.merkleRoot));
        assertTrue(updater.isValidRoot(2, header2.merkleRoot));
        assertFalse(updater.isValidRoot(1, header2.merkleRoot));
        assertFalse(updater.isValidRoot(3, header1.merkleRoot));
    }

    function test_GetLatestRoot() public {
        uint256[] memory signerKeys = new uint256[](3);
        signerKeys[0] = validatorPrivateKeys[0];
        signerKeys[1] = validatorPrivateKeys[1];
        signerKeys[2] = validatorPrivateKeys[2];

        assertEq(updater.getLatestRoot(), bytes32(0)); // Initially empty

        Updater.BlockHeader memory header1 = createBlockHeader({
            blockHeight: 1,
            merkleRoot: MERKLE_ROOT_BLOCK_1,
            timestamp: block.timestamp,
            parentHash: bytes32(0)
        });
        updater.submitHeader(header1, signHeader(header1, signerKeys));

        assertEq(updater.getLatestRoot(), header1.merkleRoot);

        Updater.BlockHeader memory header2 = createBlockHeader({
            blockHeight: 2,
            merkleRoot: MERKLE_ROOT_BLOCK_2,
            timestamp: block.timestamp + 10,
            parentHash: header1.blockHash
        });
        updater.submitHeader(header2, signHeader(header2, signerKeys));

        assertEq(updater.getLatestRoot(), header2.merkleRoot);
    }
}
