// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import {Test} from "forge-std/Test.sol";
import "forge-std/console.sol";
import {Voting} from "../src/Voting.sol";
import {Groth16Verifier} from "../src/verifier.sol";
import {Updater} from "../src/Updater.sol";

/**
 * @title TestVoteCounting - Test vote counting and winner selection
 */
contract TestVoteCounting is Test {
    Voting public voting;
    Groth16Verifier public verifier;
    Updater public updater;

    address public owner;
    uint256 public constant ELECTION_ID = 42;
    uint256 public constant NUM_CANDIDATES = 5; // Small number for testing

    // Validator setup
    address[] public validators;
    uint256[] public validatorPrivateKeys;
    uint256 public constant THRESHOLD = 3;

    function setUp() public {
        owner = address(this);

        // Setup validators
        for (uint256 i = 0; i < 5; i++) {
            uint256 privKey = 0x1000 + i;
            address validator = vm.addr(privKey);
            validators.push(validator);
            validatorPrivateKeys.push(privKey);
        }

        // Deploy contracts
        verifier = new Groth16Verifier();
        updater = new Updater(validators, THRESHOLD);
        voting = new Voting(
            address(verifier),
            address(updater),
            ELECTION_ID,
            NUM_CANDIDATES
        );

        // Add a mock block header to updater
        bytes32 mockRoot = bytes32(uint256(0x123456));
        bytes32 mockBlockHash = bytes32(uint256(0x789abc));

        Updater.BlockHeader memory header = Updater.BlockHeader({
            blockHeight: 1,
            merkleRoot: mockRoot,
            timestamp: block.timestamp,
            parentHash: bytes32(0),
            blockHash: mockBlockHash
        });

        // Create header hash for signing
        bytes32 headerHash = keccak256(
            abi.encode(
                header.blockHeight,
                header.merkleRoot,
                header.timestamp,
                header.parentHash,
                header.blockHash
            )
        );

        bytes[] memory signatures = new bytes[](3);
        for (uint256 i = 0; i < 3; i++) {
            (uint8 v, bytes32 r, bytes32 s) = vm.sign(
                validatorPrivateKeys[i],
                headerHash
            );
            signatures[i] = abi.encodePacked(r, s, v);
        }

        updater.submitHeader(header, signatures);
    }

    /*//////////////////////////////////////////////////////////////
                        MOCK VOTE SUBMISSION
    //////////////////////////////////////////////////////////////*/

    function mockVote(uint256 candidateId, address voter) internal {
        // Create mock proof (will fail verifier but we can test other logic)
        uint256[2] memory a = [uint256(1), uint256(2)];
        uint256[2][2] memory b = [
            [uint256(3), uint256(4)],
            [uint256(5), uint256(6)]
        ];
        uint256[2] memory c = [uint256(7), uint256(8)];

        // Create unique nullifier for each voter
        uint256 nullifierHash = uint256(
            keccak256(abi.encodePacked(voter, candidateId, block.timestamp))
        );

        uint256[4] memory publicSignals = [
            nullifierHash,
            ELECTION_ID,
            uint256(0x123456), // merkleRoot
            uint256(9) // commitment
        ];

        // Mock the verifier to return true
        vm.mockCall(
            address(verifier),
            abi.encodeWithSelector(Groth16Verifier.verifyProof.selector),
            abi.encode(true)
        );

        vm.prank(voter);
        voting.submitVoteLatest(a, b, c, publicSignals, candidateId);
    }

    /*//////////////////////////////////////////////////////////////
                        VOTE COUNTING TESTS
    //////////////////////////////////////////////////////////////*/

    function test_GetCandidateVotes() public {
        // Initially all candidates have 0 votes
        for (uint256 i = 0; i < NUM_CANDIDATES; i++) {
            assertEq(voting.getCandidateVotes(i), 0);
        }

        // Vote for candidate 0
        mockVote(0, address(0x1));
        assertEq(voting.getCandidateVotes(0), 1);

        // Vote for candidate 2
        mockVote(2, address(0x2));
        assertEq(voting.getCandidateVotes(2), 1);

        // Another vote for candidate 0
        mockVote(0, address(0x3));
        assertEq(voting.getCandidateVotes(0), 2);
    }

    function test_GetAllVotes() public {
        // Vote distribution: [2, 0, 3, 1, 0]
        mockVote(0, address(0x1));
        mockVote(0, address(0x2));
        mockVote(2, address(0x3));
        mockVote(2, address(0x4));
        mockVote(2, address(0x5));
        mockVote(3, address(0x6));

        uint256[] memory allVotes = voting.getAllVotes();

        assertEq(allVotes.length, NUM_CANDIDATES);
        assertEq(allVotes[0], 2, "Candidate 0 should have 2 votes");
        assertEq(allVotes[1], 0, "Candidate 1 should have 0 votes");
        assertEq(allVotes[2], 3, "Candidate 2 should have 3 votes");
        assertEq(allVotes[3], 1, "Candidate 3 should have 1 vote");
        assertEq(allVotes[4], 0, "Candidate 4 should have 0 votes");
    }

    /*//////////////////////////////////////////////////////////////
                        WINNER SELECTION TESTS
    //////////////////////////////////////////////////////////////*/

    function test_GetWinner_SingleWinner() public {
        // Candidate 2 wins with 5 votes
        mockVote(0, address(0x1));
        mockVote(0, address(0x2));
        mockVote(1, address(0x3));
        mockVote(2, address(0x4));
        mockVote(2, address(0x5));
        mockVote(2, address(0x6));
        mockVote(2, address(0x7));
        mockVote(2, address(0x8));

        (uint256 winnerId, uint256 winnerVotes) = voting.getWinner();

        assertEq(winnerId, 2, "Candidate 2 should win");
        assertEq(winnerVotes, 5, "Winner should have 5 votes");
    }

    function test_GetWinner_TieBreaker() public {
        // Tie: Candidate 1 and 3 both have 2 votes
        // Should return lowest ID (candidate 1)
        mockVote(1, address(0x1));
        mockVote(1, address(0x2));
        mockVote(3, address(0x3));
        mockVote(3, address(0x4));

        (uint256 winnerId, uint256 winnerVotes) = voting.getWinner();

        assertEq(winnerId, 1, "In a tie, lowest candidate ID wins");
        assertEq(winnerVotes, 2, "Winner should have 2 votes");
    }

    function test_GetWinner_AllVotesForOne() public {
        // All votes go to candidate 4
        mockVote(4, address(0x1));
        mockVote(4, address(0x2));
        mockVote(4, address(0x3));

        (uint256 winnerId, uint256 winnerVotes) = voting.getWinner();

        assertEq(winnerId, 4, "Candidate 4 should win");
        assertEq(winnerVotes, 3, "Winner should have 3 votes");
    }

    function test_GetWinner_RevertsWithNoVotes() public {
        vm.expectRevert("No votes yet");
        voting.getWinner();
    }

    /*//////////////////////////////////////////////////////////////
                        TOTAL VOTES TEST
    //////////////////////////////////////////////////////////////*/

    function test_TotalVotesIncrement() public {
        assertEq(voting.getTotalVotes(), 0);

        mockVote(0, address(0x1));
        assertEq(voting.getTotalVotes(), 1);

        mockVote(1, address(0x2));
        assertEq(voting.getTotalVotes(), 2);

        mockVote(0, address(0x3));
        assertEq(voting.getTotalVotes(), 3);
    }

    /*//////////////////////////////////////////////////////////////
                        ADMIN FUNCTIONS TEST
    //////////////////////////////////////////////////////////////*/

    function test_SetNumCandidates() public {
        assertEq(voting.numCandidates(), NUM_CANDIDATES);

        voting.setNumCandidates(10);
        assertEq(voting.numCandidates(), 10);

        // Should be able to get votes for new candidates
        uint256[] memory allVotes = voting.getAllVotes();
        assertEq(allVotes.length, 10);
    }

    function test_SetNumCandidates_RevertsIfZero() public {
        vm.expectRevert("Number of candidates must be greater than 0");
        voting.setNumCandidates(0);
    }

    /*//////////////////////////////////////////////////////////////
                        SCENARIO TESTS
    //////////////////////////////////////////////////////////////*/

    function test_FullElectionScenario() public {
        console.log("=== Starting Full Election Scenario ===");

        // 10 voters, 5 candidates
        // Expected results:
        // Candidate 0: 3 votes
        // Candidate 1: 1 vote
        // Candidate 2: 4 votes (WINNER)
        // Candidate 3: 2 votes
        // Candidate 4: 0 votes

        mockVote(0, address(0x101));
        mockVote(0, address(0x102));
        mockVote(0, address(0x103));

        mockVote(1, address(0x201));

        mockVote(2, address(0x301));
        mockVote(2, address(0x302));
        mockVote(2, address(0x303));
        mockVote(2, address(0x304));

        mockVote(3, address(0x401));
        mockVote(3, address(0x402));

        // Check individual votes
        assertEq(voting.getCandidateVotes(0), 3);
        assertEq(voting.getCandidateVotes(1), 1);
        assertEq(voting.getCandidateVotes(2), 4);
        assertEq(voting.getCandidateVotes(3), 2);
        assertEq(voting.getCandidateVotes(4), 0);

        // Check total
        assertEq(voting.getTotalVotes(), 10);

        // Check winner
        (uint256 winnerId, uint256 winnerVotes) = voting.getWinner();
        assertEq(winnerId, 2, "Candidate 2 should be the winner");
        assertEq(winnerVotes, 4, "Winner should have 4 votes");

        // Check all votes array
        uint256[] memory allVotes = voting.getAllVotes();
        assertEq(allVotes[0], 3);
        assertEq(allVotes[1], 1);
        assertEq(allVotes[2], 4);
        assertEq(allVotes[3], 2);
        assertEq(allVotes[4], 0);

        // --- SỬA TẠI ĐÂY ---
        console.log("Winner Candidate ID:", winnerId);
        console.log("Vote Count:", winnerVotes);
    }

    function test_GetWinner_AfterChangingNumCandidates() public {
        // Vote with 5 candidates
        mockVote(2, address(0x1));
        mockVote(2, address(0x2));
        mockVote(3, address(0x3));

        (uint256 winnerId, uint256 winnerVotes) = voting.getWinner();
        assertEq(winnerId, 2);
        assertEq(winnerVotes, 2);

        // Increase to 10 candidates (doesn't affect existing votes)
        voting.setNumCandidates(10);

        // Winner should still be candidate 2
        (winnerId, winnerVotes) = voting.getWinner();
        assertEq(winnerId, 2);
        assertEq(winnerVotes, 2);
    }
}
