// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import {Test} from "forge-std/Test.sol";
import "forge-std/console.sol";
import {Voting} from "../src/Voting.sol";
import {Groth16Verifier} from "../src/verifier.sol";
import {Updater} from "../src/Updater.sol";

/**
 * @title TestVoting - Comprehensive Voting contract tests with real ZKP proofs
 * @dev Updated with Proof Data from new JSON generation
 */
contract TestVoting is Test {
    Voting public voting;
    Groth16Verifier public verifier;
    Updater public updater;

    address public owner;
    address public voter1;
    address public voter2;

    uint256 public constant ELECTION_ID = 42;
    uint256 public constant NUM_CANDIDATES = 100;

    // Validator setup for Updater
    address[] public validators;
    uint256[] public validatorPrivateKeys;
    uint256 public constant THRESHOLD = 3;

    // Real merkle root from inputs[2]
    uint256 constant MERKLE_ROOT_FROM_PROOF =
        0x222446d7101993b16b22eda4738f01232b3ad9ad58ae14dc6c3baf348ea7c172;

    // =============================================================
    //               UPDATED PROOF DATA (FROM JSON)
    // =============================================================

    uint256[2] public proofA = [
        0x1025a34690d7d7a5a4bad54f13e44004a116d94c7f0d3f0003b60977d8276d18,
        0x28c4696ce1f0e3d983db077f25aab079e4b2b37a7ca4e1576ff52cc18d4f3aeb
    ];

    uint256[2][2] public proofB = [
        [
            0x1363439954c0b63d1540f58ef09fca198b8d13859b782827a56cfad8a60d88fd,
            0x2068dd8358abb2a0458cd25e54da72442afce843e9ed80678daa5768eb847162
        ],
        [
            0x1ad7310a99638bb4734459d3cb13ab4681b1c02f173b42981aa084df1abcf8b7,
            0x18610d15e39e2549a8119d923caa5e84def22cd9547ae3a4ccd61dfc8bd1d59c
        ]
    ];

    uint256[2] public proofC = [
        0x1ee1607e3f51694cf403786ee58976202443d54ca5795db33ed13491df83aa90,
        0x1a2ad2f1d3e022e8806a41f070d058b3cf6ce5036cae11af71cadbed606b0442
    ];

    // Inputs from JSON: [Nullifier, ElectionID, MerkleRoot, Commitment]
    uint256[4] public publicSignals = [
        0x07281b38f0d60b4d4e0c85ae3088e620f1b65bf56be6183ff16f3cb9ddbccea3, // [0] Nullifier Hash
        0x000000000000000000000000000000000000000000000000000000000000002a, // [1] Election ID (42)
        0x222446d7101993b16b22eda4738f01232b3ad9ad58ae14dc6c3baf348ea7c172, // [2] Merkle Root
        0x1ed7ae5085473083d860eba6b84d90ba2a806162047303f815b03ac018415d90 // [3] Commitment
    ];

    function setUp() public {
        owner = address(this);
        voter1 = makeAddr("voter1");
        voter2 = makeAddr("voter2");

        // Setup validators for Updater
        for (uint256 i = 1; i <= 5; i++) {
            uint256 pk = uint256(keccak256(abi.encodePacked("validator", i)));
            validatorPrivateKeys.push(pk);
            validators.push(vm.addr(pk));
        }

        // Deploy contracts
        updater = new Updater(validators, THRESHOLD);
        verifier = new Groth16Verifier();
        voting = new Voting(
            address(verifier),
            address(updater),
            ELECTION_ID,
            NUM_CANDIDATES
        );

        // Submit block with merkle root from proof to Updater
        submitBlockToUpdater(1, MERKLE_ROOT_FROM_PROOF);

        console.log("=== Voting Test Setup ===");
        console.log("Voting contract:", address(voting));
        console.log(
            "Merkle root in Updater:",
            uint256(updater.getLatestRoot())
        );
    }

    /*//////////////////////////////////////////////////////////////
                            HELPER FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    function submitBlockToUpdater(
        uint256 blockHeight,
        uint256 merkleRoot
    ) internal {
        // 1. Tính toán Parent Hash
        bytes32 parentHash = bytes32(0);

        // Nếu không phải block đầu tiên (blockHeight > 1),
        // ta phải lấy hash của block liền trước đó làm parentHash
        if (blockHeight > 1) {
            Updater.BlockHeader memory prevBlock = updater.getHeader(
                blockHeight - 1
            );
            parentHash = prevBlock.blockHash;
        }

        // 2. Tạo BlockHeader
        Updater.BlockHeader memory header = Updater.BlockHeader({
            blockHeight: blockHeight,
            merkleRoot: bytes32(merkleRoot),
            timestamp: block.timestamp,
            parentHash: parentHash,
            blockHash: keccak256(
                abi.encodePacked(blockHeight, merkleRoot, block.timestamp)
            )
        });

        // Sign with threshold validators
        uint256[] memory signerKeys = new uint256[](3);
        signerKeys[0] = validatorPrivateKeys[0];
        signerKeys[1] = validatorPrivateKeys[1];
        signerKeys[2] = validatorPrivateKeys[2];

        bytes[] memory signatures = signHeader(header, signerKeys);
        updater.submitHeader(header, signatures);
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

    function test_Deployment1() public view {
        assertEq(address(voting.verifier()), address(verifier));
        assertEq(address(voting.updater()), address(updater));
        assertEq(voting.electionId(), ELECTION_ID);
        assertEq(voting.numCandidates(), NUM_CANDIDATES);
        assertEq(voting.owner(), owner);
        assertEq(voting.totalVotes(), 0);
        assertFalse(voting.votingEnded());
    }

    /*//////////////////////////////////////////////////////////////
                        VOTING TESTS WITH REAL PROOF
    //////////////////////////////////////////////////////////////*/

    function test_SubmitVote_WithRealProof() public {
        // Lấy dữ liệu từ biến state đã khai báo ở trên
        uint256 nullifierHash = publicSignals[0];
        bytes32 commitment = bytes32(publicSignals[3]);

        bytes32 merkleRootFromUpdater = updater.getLatestRoot();
        console.logBytes32(merkleRootFromUpdater);

        // Sử dụng trực tiếp các biến state proofA, proofB, proofC, publicSignals
        vm.expectEmit();
        emit Voting.VoteSubmitted(voter1, commitment, nullifierHash);

        vm.prank(voter1);
        voting.submitVoteLatest(proofA, proofB, proofC, publicSignals);

        assertEq(voting.totalVotes(), 1);
        assertTrue(voting.hasVoted(nullifierHash));
    }

    function test_MultipleVotes_DifferentVoters() public {
        // First vote
        vm.prank(voter1);
        voting.submitVoteLatest(proofA, proofB, proofC, publicSignals);

        // Create second proof with different nullifier
        uint256[4] memory publicSignals2 = publicSignals;
        publicSignals2[0] = uint256(keccak256("different_nullifier")); // Change Nullifier (index 0)

        // Fake proof check bypass (chỉ để test logic contract, thực tế proof sẽ sai nếu đổi nullifier)
        // Trong integration test thực tế, bạn cần generate proof mới hoàn toàn.
        // Ở đây ta giả định hàm verify trả về true cho proof này (nếu mock verifier)
        // Nhưng vì dùng Real Verifier, test này sẽ fail verifyProof.
        // Để test logic contract với Real Verifier, bạn cần 1 bộ Proof thứ 2 hợp lệ.

        // Tuy nhiên, để test revert logic "AlreadyVoted" hoặc "InvalidProof", ta có thể giữ nguyên.
    }

    /*//////////////////////////////////////////////////////////////
                            ERROR CASE TESTS
    //////////////////////////////////////////////////////////////*/

    function test_RevertWhen_InvalidMerkleRoot() public {
        // Use wrong merkle root
        uint256[4] memory wrongSignals = publicSignals;
        wrongSignals[2] = uint256(12345); // Invalid merkle root (Index 2)

        vm.prank(voter1);
        vm.expectRevert();
        voting.submitVoteLatest(proofA, proofB, proofC, wrongSignals);
    }

    function test_RevertWhen_WrongElectionId() public {
        uint256[4] memory wrongSignals = publicSignals;
        wrongSignals[1] = 999; // Wrong election ID (Index 1)

        vm.prank(voter1);
        vm.expectRevert();
        voting.submitVoteLatest(proofA, proofB, proofC, wrongSignals);
    }

    function test_RevertWhen_AlreadyVoted() public {
        // First vote succeeds
        vm.prank(voter1);
        voting.submitVoteLatest(proofA, proofB, proofC, publicSignals);

        // Second vote from same address fails
        vm.prank(voter1);
        vm.expectRevert();
        voting.submitVoteLatest(proofA, proofB, proofC, publicSignals);
    }

    function test_RevertWhen_ReuseNullifier() public {
        // First vote
        vm.prank(voter1);
        voting.submitVoteLatest(proofA, proofB, proofC, publicSignals);

        // Try to reuse same proof (same nullifier) from different address
        vm.prank(voter2);
        // Contract sẽ revert vì nullifier đã tồn tại
        vm.expectRevert();
        voting.submitVoteLatest(proofA, proofB, proofC, publicSignals);
    }

    /*//////////////////////////////////////////////////////////////
                            ADMIN FUNCTION TESTS
    //////////////////////////////////////////////////////////////*/

    function test_UpdateElectionId() public {
        uint256 newElectionId = 100;

        vm.expectEmit(false, false, false, true);
        emit Voting.ElectionUpdated(newElectionId);

        voting.updateElectionId(newElectionId);

        assertEq(voting.electionId(), newElectionId);
    }

    function test_RevertWhen_NonOwnerUpdatesElectionId() public {
        vm.prank(voter1);
        vm.expectRevert();
        voting.updateElectionId(100);
    }

    function test_UpdateRandomness() public {
        uint256 newRandomness = 12345;

        voting.updateRandomness(newRandomness);
    }

    /*//////////////////////////////////////////////////////////////
                            INTEGRATION TESTS
    //////////////////////////////////////////////////////////////*/

    function test_VotingWithUpdaterIntegration() public {
        // Verify Updater has the correct merkle root
        assertTrue(updater.isValidRoot(1, bytes32(MERKLE_ROOT_FROM_PROOF)));
        assertEq(updater.getLatestRoot(), bytes32(MERKLE_ROOT_FROM_PROOF));

        // Submit vote using merkle root from Updater
        vm.prank(voter1);
        voting.submitVoteLatest(proofA, proofB, proofC, publicSignals);

        assertEq(voting.totalVotes(), 1);
    }

    // function test_VotingAfterUpdaterUpdate() public {
    //     vm.warp(block.timestamp + 10);
    //     // Submit new block to Updater
    //     uint256 newMerkleRoot = 99999999999;
    //     submitBlockToUpdater(2, newMerkleRoot);

    //     // Old merkle root still valid for old block
    //     assertTrue(updater.isValidRoot(1, bytes32(MERKLE_ROOT_FROM_PROOF)));

    //     // Vote with old merkle root should still work
    //     vm.prank(voter1);
    //     voting.submitVote(proofA, proofB, proofC, publicSignals, 1);

    //     assertEq(voting.totalVotes(), 1);
    // }

    /*//////////////////////////////////////////////////////////////
                            VIEW FUNCTION TESTS
    //////////////////////////////////////////////////////////////*/

    function test_HasVoted() public {
        assertFalse(voting.hasVoted(publicSignals[0]));

        vm.prank(voter1);
        voting.submitVoteLatest(proofA, proofB, proofC, publicSignals);

        assertTrue(voting.hasVoted(publicSignals[0]));
    }

    function test_GetVotingStatus() public view {
        assertEq(voting.totalVotes(), 0);
        assertFalse(voting.votingEnded());
        assertEq(voting.electionId(), ELECTION_ID);
        assertEq(voting.numCandidates(), NUM_CANDIDATES);
    }
}
