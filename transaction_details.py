
daemon_rpc_port='17750' # Online daemon
start_block=1620000

####################
####################
####################
#     START
####################
####################
####################

import requests
import json	
import decimal

headers = {'Content-Type': 'application/json',}


def find_key_in_json(json_obj,key_name): #Finds a certain key in a json
	return_val=None
	for key, value in json_obj.items():
		if key==key_name:
			return(value)
		if isinstance(value, dict):
			a=find_key_in_json(value, key_name)
			if a is not None:
				return(a)
	return return_val

def find_first_output_for_block(block_height): #Finds the first output generated in a certain block
	if block_height==0:
		return(0)
	if block_height==1:
		return(1)
	start_pow2=23
	for i in range(1,10):
		start_pow2+=1
		data='{"jsonrpc":"2.0","id":"0","get_txid":true,"outputs":[{"amount":0,"index":'+str(2**start_pow2)+'}]}'
		response = requests.post('http://127.0.0.1:'+daemon_rpc_port+'/get_outs', headers=headers, data=data)
		json_obj = json.loads(response.content.decode())
		if 'outs' not in json_obj:
			break
	
	pow2=start_pow2-1

	block_at=0
	for i in range(0,start_pow2-1):
		data='{"jsonrpc":"2.0","id":"0","get_txid":true,"outputs":[{"amount":0,"index":'+str(2**pow2)+'}]}'
		response = requests.post('http://127.0.0.1:'+daemon_rpc_port+'/get_outs', headers=headers, data=data)
		json_obj = json.loads(response.content.decode())
		if 'outs' in json_obj:
			block_at=json_obj['outs'][0]['height']			
			if block_at<block_height:
				break
		pow2-=1
	
	out_at=2**pow2

	for i in reversed(range(0, pow2-1)):
		out_at+=2**i
		data='{"jsonrpc":"2.0","id":"0","get_txid":true,"outputs":[{"amount":0,"index":'+str(out_at)+'}]}'
		response = requests.post('http://127.0.0.1:'+daemon_rpc_port+'/get_outs', headers=headers, data=data)
		json_obj = json.loads(response.content.decode())
		if 'outs' not in json_obj:
			out_at-=2**i
		else:
			block_at=json_obj['outs'][0]['height']
			if block_at>=block_height:
				out_at-=2**i
		

	out_at+=1	
	data='{"jsonrpc":"2.0","id":"0","get_txid":true,"outputs":[{"amount":0,"index":'+str(out_at)+'}]}'
	response = requests.post('http://127.0.0.1:'+daemon_rpc_port+'/get_outs', headers=headers, data=data)
	json_obj = json.loads(response.content.decode())
	if 'outs' not in json_obj:
		return None
	else:
		block_at=json_obj['outs'][0]['height']
		if block_at==block_height:
			return(out_at)
		else:
			return None

def as_decimal(amount): #Converts Haven amounts to decimal amounts
	if amount is None:
		return None
	else:
		return decimal.Decimal(amount)/1000000000000 


####################
#Get current block height from offline and online daemon
##################### 


#Get current blockchain height
data = '{"jsonrpc":"2.0","id":"0","method":"get_block_count"}'
response = requests.post('http://127.0.0.1:'+daemon_rpc_port+'/json_rpc', headers=headers, data=data)
json_obj = json.loads(response.content.decode())
current_height=json_obj['result']['count']


#Read blocks related data. Currently not used.
blocks_data=[]
blocks=range(start_block,current_height-1)
blocks_chunks=[blocks[i:i+1000] for i in range(0, len(blocks), 1000)]
for block_chunk in blocks_chunks:
	data='{"jsonrpc":"2.0","id":"0","method":"get_block_headers_range","params":{"start_height":'+str(block_chunk[0])+',"end_height":'+str(block_chunk[-1])+'}}'
	response = requests.post('http://127.0.0.1:'+daemon_rpc_port+'/json_rpc', headers=headers, data=data)
	json_obj = json.loads(response.content.decode())
	for res in zip(json_obj['result']['headers'], block_chunk):
		blocks_data.append([res[1], res[0]['reward']])


#In order to analyze transactions, we need a way to obtain their transaction hashes
#The fasted way to do that in bulk appears to be to use the get_outs RPC method, as get_block only returns the transaction hashes for one block
#So first we find the first and last out of our block range, which is defined as (start_block,current blockchain height-2)
start_out=find_first_output_for_block(start_block)
end_out=find_first_output_for_block(current_height-1)-1

#Get all combinations of (output_id, block,transaction) for the range 
out_range=range(start_out, end_out)
all_outputs=[]
outs_chunks=[out_range[i:i+1000] for i in range(0, len(out_range), 1000)]
for outs_chunk in outs_chunks:
	outs_rpc=','.join('{"amount":0,"index":'+str(k)+'}' for k in outs_chunk)
	data='{"jsonrpc":"2.0","id":"0","get_txid":true,"outputs":['+outs_rpc+']}'
	response = requests.post('http://127.0.0.1:'+daemon_rpc_port+'/get_outs', headers=headers, data=data)
	json_obj = json.loads(response.content.decode())
	if 'outs' not in json_obj:
		print('Error')
		quit()
	for out_rec in zip(json_obj['outs'],outs_chunk):
		all_outputs.append([out_rec[1], out_rec[0]['height'], out_rec[0]['txid']])

#Get all combinations of (block,transaction) for the range 
all_txns=[]
for output in all_outputs:	
	if len(all_txns)==0:
		all_txns.append([output[1], output[2]])
	else:
		if output[2]!=all_txns[-1][1]:
			all_txns.append([output[1], output[2]])


#Now get transaction data using the get_transactions method, 1000 transactions at a time
#Parse the json and print some useful output
all_txns_chunks=[all_txns[i:i+1000] for i in range(0, len(all_txns), 1000)]
for txns_chunks in all_txns_chunks:
	tx_hashes_rpc=','.join('"'+k[1]+'"' for k in txns_chunks)
	data='{"txs_hashes":['+tx_hashes_rpc+'],"decode_as_json":true}'
	response = requests.post('http://127.0.0.1:'+daemon_rpc_port+'/get_transactions', headers=headers, data=data)
	json_obj = json.loads(response.content.decode())
	txs_as_json=json_obj['txs_as_json']
	for tx_json in zip(txns_chunks, txs_as_json):
		tx_block=tx_json[0][0]
		tx_hash=tx_json[0][1]
		json_obj = json.loads(tx_json[1])

		result_row=[]
		result_row.append(tx_block) # Transaction block height
		result_row.append(tx_hash)  # Transaction hash
		is_miner_tx=False
		if 'gen' in json_obj['vin'][0]:
			is_miner_tx=True
		result_row.append(is_miner_tx)  # Is it a miner transaction
		
		input_assets=[]	
		for inp in json_obj['vin']:
			if 'gen' not in inp:			
				input_assets.append(find_key_in_json(inp, 'asset_type'))

		output_assets=[]	
		for output in json_obj['vout']:		
			output_assets.append(find_key_in_json(output, 'asset_type'))
		
		
		result_row.append(len(input_assets)) #Number of inputs
		result_row.append(len(output_assets)) #Number of outputs
		result_row.append(set(input_assets)) #Distinct inputs
		result_row.append(set(output_assets)) #Distinct outputs
		result_row.append(as_decimal(find_key_in_json(json_obj, 'txnFee'))) # txnFee
		result_row.append(as_decimal(find_key_in_json(json_obj, 'txnOffshoreFee'))) # txnOffshoreFee
		result_row.append(as_decimal(find_key_in_json(json_obj, 'amount_burnt'))) # Amount burnt
		result_row.append(as_decimal(find_key_in_json(json_obj, 'amount_minted'))) # Amount minted
		if is_miner_tx:
			miner_outs=[]		
			for output in json_obj['vout']:	
				miner_outs.append([str(as_decimal(find_key_in_json(output,'amount'))), find_key_in_json(output,'asset_type')])
			result_row.append(miner_outs) #Miner outputs
		else:
			result_row.append(None)
		
		result_row_str=';'.join(str(k) for k in result_row)
		print(result_row_str)


