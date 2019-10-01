<?php
include 'lib/MyCypher.php';

$iv = 'asdf';
$key = 'Hallo123';
$cypher = new MyCypher($iv=$iv, $key=$key);
$php_encrypted = $cypher->encrypt('oliver@linux-kernel.at');
print($php_encrypted);
