import express, { Request, Response } from 'express';
import https from 'https';
import path from 'path';
import fs from "fs";

function parse_input_arg(key:string){
    const args = process.argv.slice(2)
    const key_index = args.indexOf(key);
    const value = args.at(key_index+1)
    if (value) {
        console.log(`[INFO]: input arg ${key} has value ${value}`);
    }
    else {
        console.log(`[ERROR]: please specify '${key} {value}'`);
        process.exit(-1);
    }
    return value
}

var host = parse_input_arg("-ip")
var server_key_path = parse_input_arg("-server_key_path")
var server_cer_path = parse_input_arg("-server_cer_path")

const server = express();
server.use(express.static(path.join(__dirname, 'public')));
server.get('/', (req: Request, res: Response) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

const tls_configuration = {
    key: fs.readFileSync(server_key_path),
    cert: fs.readFileSync(server_cer_path),
  };

https.createServer(tls_configuration, server).listen(443, host, ()=> {
    console.log(`[INFO]: 🚀 HTTPS Server running...`);
});
