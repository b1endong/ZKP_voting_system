const circomlib = require("circomlibjs");

async function main() {
    const poseidon = await circomlib.buildPoseidon();
    const F = poseidon.F;

    // Input test
    const secret = 123n;
    const pathElements = [888888n, 999999n];
    const pathIndices = [0, 1];

    // Bắt đầu với leaf = Poseidon(secret)
    let cur = poseidon([secret]);

    for (let i = 0; i < pathElements.length; i++) {
        if (pathIndices[i] === 0) {
            cur = poseidon([cur, pathElements[i]]);
        } else {
            cur = poseidon([pathElements[i], cur]);
        }
    }

    console.log("Merkle Root:", F.toString(cur));
}

main();
