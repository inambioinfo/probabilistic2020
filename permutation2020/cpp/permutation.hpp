#include <map>
#include <cmath>
#include <string>

#define M_LOG2E 1.44269504088896340736L //log2(e)

/* Log base 2 */
inline long double log2(const long double x){
    return  log(x) * M_LOG2E;
}

/* Calculates all position-based statistics in one function.
 * Specifically it calculates:
 * 1. number of recurrent missense mutations
 * 2. fraction of uniform missense entropy
 * 3. delta entropy of missense entropy compared to uniform
 *
 * Parameters
 * ----------
 * pos_ctr : map<int, int>
 *      maps positions to number of mutations
 *
 * Returns
 * -------
 * out : map<string, double>
 *      STL map contianer containing position statistics
 */
std::map<std::string, double> calc_position_statistics(std::map<int, int> pos_ctr){
    int recurrent_sum = 0, val = 0;
    long double myent_2 = 0.0L, myent_e = 0.0L, mysum = 0.0L, p = 0.0L;
    long double frac_of_uniform_ent = 1.0L, num_pos = 0.0L;
    long double delta_ent = 0.0L;
    std::map<std::string, double> out;
    typedef std::map<int, int>::iterator it_type;

    // count total mutations
    for(it_type iterator = pos_ctr.begin(); iterator != pos_ctr.end(); iterator++) {
        val = iterator->second;
        if (val>1){
            recurrent_sum += val;
        }
        mysum += val;
    }

    // calculate entropy 
    for(it_type iterator = pos_ctr.begin(); iterator != pos_ctr.end(); iterator++) {
        val = iterator->second;
        p = val / mysum;
        myent_2 -= p * log2(p);
        myent_e -= p * log(p);
        num_pos += 1;
    }
    if (num_pos > 1) {
        delta_ent = log(num_pos) - myent_e;
    }
    if (mysum > 1) {
        frac_of_uniform_ent = myent_2 / log2(mysum);
    }

    // put output in a map container
    out["recurrent"] = recurrent_sum;
    out["entropy_fraction"] = frac_of_uniform_ent;
    out["delta_entropy"] = delta_ent;
    return(out);
}
