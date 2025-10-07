// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import {Groth16Verifier} from "../src/verifier.sol";
import {Voting} from "../src/Voting.sol";
import "forge-std/Test.sol";

event VoteSubmitted(address indexed voter, bytes32 commitment);

contract TestVoting is Test {
    address voter = makeAddr("voter");
    address owner = makeAddr("owner");
    uint256 constant electionId = 42;
    bytes32 constant merkleRoot =
        bytes32((uint256(16913408437976580737476875716108326861435185907917839778183277611231320791399)));
    uint256 constant numCandidates = 4;
    Groth16Verifier verifier;
    Voting voting;

    function setUp() public {
        vm.startPrank(owner);
        verifier = new Groth16Verifier();
        voting = new Voting(address(verifier), electionId, merkleRoot, numCandidates);
        vm.stopPrank();
    }

    function testSetUp() public view {
        assertEq(address(voting.getVerifier()), address(verifier));
        assertEq(voting.owner(), owner);
        assertEq(voting.electionId(), electionId);
        assertEq(voting.merkleRoot(), merkleRoot);
        assertEq(voting.numCandidates(), numCandidates);
    }

    function testSubmitVote() public {
        uint256[2] memory a = [
            15608700142076136814303480697387047395415609491952961610168001705919399676989,
            4623412535244763165360108738812805372429177949101816737438915236157070447801
        ];
        uint256[2][2] memory b = [
            [
                689827727749238677123752538342534702411188208806308946048325755270859554962,
                13355701049275319022297906269272516446970708867575769343872490717744621412985
            ],
            [
                11185546216178623567727344436470883095765133350769913038277192129741098540939,
                12310632246068911907263358575531838917304335184546125674058077726054073116580
            ]
        ];
        uint256[2] memory c = [
            12613993421025885958955581681315989524717529924765682243130714621885740248162,
            7399454475275607435084253403724195490446520699631798340000287934719430206786
        ];
        uint256[1] memory publicSignals =
            [uint256(17141541128951136205286884206867621936295882637835868708156565111199086946105)];
        bytes32 commitment =
            bytes32(uint256(11341982949512057884670737814841439623351848605901602460849116037414548552753));
        vm.startPrank(voter);
        vm.expectEmit();
        emit VoteSubmitted(voter, commitment);

        voting.submitVote(a, b, c, publicSignals, commitment);

        assertEq(voting.getTotalVotes(), 1);
        vm.stopPrank();
    }

    function testRevertDoubleVoting() public {
        uint256[2] memory a = [
            15608700142076136814303480697387047395415609491952961610168001705919399676989,
            4623412535244763165360108738812805372429177949101816737438915236157070447801
        ];
        uint256[2][2] memory b = [
            [
                689827727749238677123752538342534702411188208806308946048325755270859554962,
                13355701049275319022297906269272516446970708867575769343872490717744621412985
            ],
            [
                11185546216178623567727344436470883095765133350769913038277192129741098540939,
                12310632246068911907263358575531838917304335184546125674058077726054073116580
            ]
        ];
        uint256[2] memory c = [
            12613993421025885958955581681315989524717529924765682243130714621885740248162,
            7399454475275607435084253403724195490446520699631798340000287934719430206786
        ];
        uint256[1] memory publicSignals =
            [uint256(17141541128951136205286884206867621936295882637835868708156565111199086946105)];
        bytes32 commitment =
            bytes32(uint256(11341982949512057884670737814841439623351848605901602460849116037414548552753));

        //First vote sumbmitted successfully
        vm.prank(voter);
        voting.submitVote(a, b, c, publicSignals, commitment);
        assertEq(voting.getTotalVotes(), 1);
        //Second vote reverts
        vm.expectRevert();
        vm.prank(voter);
        voting.submitVote(a, b, c, publicSignals, commitment);
        assertEq(voting.getTotalVotes(), 1);
    }

    function testRevertInvalidProof() public {
        uint256[2] memory a = [
            12508700142076136814303480697387047395415609491952961610168001705919399676989,
            4623412535244763165360108738812805372429177949101816737438915236157070447801
        ];
        uint256[2][2] memory b = [
            [
                689827727749238677123752538342534702411188208806308946048325755270859554962,
                13355701049275319022297906269272516446970708867575769343872490717744621412985
            ],
            [
                11185546216178623567727344436470883095765133350769913038277192129741098540939,
                12310632246068911907263358575531838917304335184546125674058077726054073116580
            ]
        ];
        uint256[2] memory c = [
            12613993421025885958955581681315989524717529924765682243130714621885740248162,
            7399454475275607435084253403724195490446520699631798340000287934719430206786
        ];
        uint256[1] memory publicSignals =
            [uint256(17141541128951136205286884206867621936295882637835868708156565111199086946105)];
        bytes32 commitment =
            bytes32(uint256(11341982949512057884670737814841439623351848605901602460849116037414548552753));
        vm.expectRevert();
        vm.prank(voter);
        voting.submitVote(a, b, c, publicSignals, commitment);
    }
}
