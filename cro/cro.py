#-*- coding: utf-8 -*-
from __future__ import division

import os
import time
import numpy as np

class CRO(object):
    def __init__(self, Ngen, N, M, Fb, Fa, Fd, r0, k, Pd, fitness_coral, opt, L=None,
                 ke = 0.2, npolyps = 1, seed=13, mode='bin', param_grid={}, verbose=False):
        
        self.Ngen = Ngen
        self.N    = N
        self.M    = M
        self.Fb   = Fb
        self.Fa   = Fa
        self.Fd   = Fd              
        self.r0   = r0
        self.k    = k
        self.Pd   = Pd
        self.fitness_coral = fitness_coral
        self.opt  = opt           
        self.opt_multiplier = -1 if opt == "max" else 1
        self.L    = L                          
        self.ke   = ke
        self.npolyps = npolyps
        self.seed = seed
        self.mode = mode
        self.param_grid = param_grid
        self.verbose = verbose
        
        print("[*Running] Initialization: ", self.opt) 

    def reefinitialization (self):   
        """    
        function [REEF,REEFpob]=reefinitialization(M,N,r0,L)
        Description: Initialize the REEF with L-length random corals. r0 is the occupied/total rate.
        This function depends on the problem to be solved, max-ones in this case.   
        Input: 
            - MxN: reef size
            - r0: occupied/total rate
            - L: coral length
        Output:
            - REEF: reef matrix
            - REEFpob: population matrix
        """  
        
        # print error. Maybe use other place for all arg-checks
        if ( (self.param_grid=={}) & (self.mode =='disc') ):
            print('\nThis mode (', self.mode, ') needs a param_grid as a dictionary')
            return -1
 
        # commom for all modes
        np.random.seed(seed = self.seed)
        O = int(np.round(self.N*self.M*self.r0)) # number of occupied reefs 
        
        # Binary mode
        if self.mode =='bin': 
            A = np.random.randint(2, size=[O, self.L])
            B = np.zeros([( (self.N*self.M)-O), self.L], int)          
            REEFpob = np.concatenate([A,B]) # Population creation
            REEF = np.array((REEFpob.any(axis=1)),int) 
            return (REEF, REEFpob)
        
        # Discrete mode
        elif self.mode =='disc':
            for key, value in self.param_grid.items():
                valmax = (value[1] - value[0] + 1)
                A = np.random.randint(valmax, size=[O, self.L]) + value[0]
                B = np.zeros([( (self.N*self.M)-O), self.L], int)
                REEFpob = np.concatenate([A,B]) # Population creation
                REEF = np.array((REEFpob.any(axis=1)),int) 
                return (REEF, REEFpob)
        
        else: 
            print('\nThis mode (', self.mode, ') is not available')
            return -1

    def fitness(self, REEFpob):
        """
        Description:
            This function calculates the health function for each coral in the reef
        """
        REEF_fitness = []
        for coral in REEFpob:
            coral_fitness = self.fitness_coral(coral)
            REEF_fitness.append(coral_fitness)

        return self.opt_multiplier*np.array(REEF_fitness)

    def broadcastspawning(self, REEF, REEFpob): 
        """
        Description:
            Create new larvae by external sexual reproduction. Cross-over operation
        Input: 
            - REEF: coral reef
            - REEFpob: reef population
            - self.Fb: fraction of broadcast spawners with respect to the overall amount of existing corals
            - self.mode: type of crossover depending on the type. type can be set to one of these options ('cont', 'disc','bin')
        Output:
            - ESlarvae: created larvae
        """
        Fb = self.Fb

        # get  number of spawners, forzed to be even (pairs of corals to create one larva)
        np.random.seed(seed = self.seed)
        nspawners = int(np.round(Fb*np.sum(REEF)))

        if (nspawners%2) !=0: 
            nspawners=nspawners-1

        # get spawners and divide them in two groups
        p = np.where(REEF!=0)[0]
        a = np.random.permutation(p)
        spawners = a[:nspawners]
        spawners1 = REEFpob[spawners[0:int(nspawners/2)], :]
        spawners2 = REEFpob[spawners[int(nspawners/2):], :]

        # get crossover mask for some of the methods below
        (a,b) = spawners1.shape
        mask = np.random.randint(2, size=[a,b])
        
        # all zeros and all ones doesn't make sense, Not produces crossover
        pos = np.where(np.sum(mask, axis= 1)==0)[0] 
        mask[pos, np.random.randint(self.L, size=[len(pos)])] = 1
        pos = np.where(np.sum(mask, axis= 1)==1)[0]
        mask[pos, np.random.randint(self.L, size=[len(pos)])] = 0
        
        notmask = np.logical_not(mask)

        ESlarvae1 = np.multiply(spawners1, np.logical_not(mask)) + np.multiply(spawners2, mask)
        ESlarvae2 = np.multiply(spawners2, np.logical_not(mask)) + np.multiply(spawners1, mask)
        ESlarvae = np.concatenate([ESlarvae1, ESlarvae2])
        return ESlarvae

    
    def _larvaemutation(self, larvae, pos, delta=1):
        """
        Description:
            This function modifies the larvae with mutation 
        Input:
            - larvae: new individuals to be mutated
            - pos: selected positions to be mutated
            - delta: represents an increment or decrement in each mutation (it could be placed as arg in param_grid)
        Output:
            - larvae: modified individuals
        """
        (nlarvaes, b) = larvae.shape
        MM = np.zeros([nlarvaes, b], int) # Mutation matrix
        # int just for disc mode, replace when cont mode takes place

        for key, value in self.param_grid.items():
            m, M = value

        inc = (M - larvae[range(nlarvaes), pos])
        dec = (larvae[range(nlarvaes), pos] -m) 
        Inc = np.where(inc>dec)  
        Dec = np.where(inc<=dec) 
        
        MM[Inc[1], pos[Inc]] = np.random.randint(delta, np.min(inc[Inc])) if len(Inc[1]) !=0 else delta 
        MM[Dec[1], pos[Dec]] = -np.random.randint(delta, np.min(dec[Dec])) if len(Dec[1]) !=0 else -delta 

        return larvae + MM
    
    
    def brooding(self, REEF, REEFpob):
        """
        Description:
            Create new larvae by internal sexual reproduction   
        Input:
            - REEF: coral reef
            - REEFpob: reef population 
            - self.npolyps: number of polyps to be mutated (as genes in a evolutionary). 
                            Coral reefs are therefore created by millions of tiny polyps forming large carbonate structures  
            - self.Fb: fraction of broadcast spawners with respect to the overall amount of existing corals 
            - self.mode: type of crossover depending on the type. type can be set to one of these options ('cont', 'disc','bin')
        Output:
            - brooders: created larvae
        """
        
        Fb = self.Fb
        npolyps = self.npolyps
        
        # get the brooders
        np.random.seed(seed = self.seed)
        nbrooders= int(np.round((1-Fb)*np.sum((REEF))))

        p = np.where(REEF!=0)[0] 
        a = np.random.permutation(p)
        brooders = a[0:nbrooders]
        brooders = REEFpob[brooders, :]
                
        pos = np.random.randint(brooders.shape[1], size=(npolyps, nbrooders))
            
        if self.mode =='bin':
            brooders[range(nbrooders), pos] = np.logical_not(brooders[range(nbrooders), pos])
        if self.mode =='disc':
            brooders = self._larvaemutation(brooders, pos)
                        
        return brooders

    
    def _settle_larvae(self, larvae, larvaefitness,  REEF, REEFpob, REEFfitness, indices):
        """
        Description:
            Settle the given larvae in the REEF in the given indices
        """
        REEF[indices] = 1
        REEFpob[indices, :] = larvae
        REEFfitness[indices] = larvaefitness

        return REEF, REEFpob, REEFfitness

    def larvaesettling(self, REEF, REEFpob, REEFfitness, larvae, larvaefitness):
        """
        Description:
            Settle the best larvae in the reef, eliminating those which are not good enough
        Input:    
            - REEF: coral reef
            - REEFpob: reef population
            - REEFfitness: reef fitness
            - larvae: larvae population
            - larvaefitness: larvae fitness
            - self.k: number of oportunities for each larva to settle in the reef
            - self.opt: type of optimization ('min' or 'max')
        Output:
            - REEF: new coral reef
            - REEFpob: new reef population
            - REEFfitness: new reef fitness
        """
        k = self.k

        np.random.seed(seed=self.seed)
        Nlarvae = larvae.shape[0]
        nREEF = len(REEF)

        # First larvae occupy empty places
        free = np.where(REEF==0)[0]
        larvae_emptycoral = larvae[:len(free), :]
        fitness_emptycoral = larvaefitness[:len(free)]
        REEF, REEFpob, REEFfitness = self._settle_larvae(larvae_emptycoral, fitness_emptycoral,
                                                         REEF, REEFpob, REEFfitness, free)

        larvae = larvae[len(free):, :]  # update larvae
        larvaefitness = larvaefitness[len(free):] 

        for larva, larva_fitness in zip(larvae, larvaefitness):
            reef_indices = np.random.randint(nREEF, size=k)
            reef_index = reef_indices[0]

            if not REEF[reef_index]: # empty coral
                REEFpob[reef_index] = larva
                REEFfitness[reef_index] = larva_fitness
                REEF[reef_index] = 1
            else:                  # occupied coral
                fitness_comparison = larva_fitness < REEFfitness[reef_indices]

                if np.any(fitness_comparison):
                    reef_index = reef_indices[np.where(fitness_comparison)[0][0]]
                    REEF, REEFpob, REEFfitness = self._settle_larvae(larva, larva_fitness, REEF,
                                                                     REEFpob, REEFfitness, reef_index)

        return (REEF,REEFpob,REEFfitness)

    def budding(self, REEF, REEFpob, fitness):
        """
        function  [Alarvae]=budding(REEF,pob,fitness,Fa)
        Duplicate the better corals in the reef.
        Input: 
            - REEF: coral reef 
            - pob: reef population
            - fitness: reef fitness 
            - Fa: fraction of corals to be duplicated
        Output: 
            - Alarvae: created larvae,
            - Afitness: larvae's fitness
        """
        Fa = self.Fa
        
        pob = REEFpob[np.where(REEF==1)[0], :]
        fitness = fitness[np.where(REEF==1)]
        N = pob.shape[0]
        NA = int(np.round(Fa*N))
        
        ind = np.argsort(fitness)    
            
        fitness = fitness[ind]
        Alarvae = pob[ind[0:NA], :]
        Afitness = fitness[0:NA]
        return (Alarvae, Afitness)

    def depredation(self, REEF, REEFpob, REEFfitness):    
        """
        function [REEF,REEFpob,REEFfitness]=depredation(REEF,REEFpob,REEFfitness,Fd,Pd,opt)
        Depredation operator. A fraction Fd of the worse corals is eliminated with probability Pd
        Input:
            - REEF: coral reef
            - REEFpob: reef population
            - REEFfitness: reef fitness
            - self.Fd: fraction of the overall corals to be eliminated
            - self.Pd: probability of eliminating a coral
            - self.opt: type of optimization ('min' or 'max')
        Output:
            - REEF: new coral reef
            - REEFpob: new reef population
            - REEFfitness: new reef fitness
         """ 
        
        Fd = self.Fd
        Pd = self.Pd
        np.random.seed(seed = self.seed)
        
        # Sort by worse fitness (hence the minus sign)
        ind = np.argsort(-REEFfitness)

        sortind = ind[:int(np.round(Fd*REEFpob.shape[0]))]
        p = np.random.rand(len(sortind))
        dep = np.where(p<Pd)[0]
        REEF[sortind[dep]] = 0
        REEFpob[sortind[dep], :] = self.empty_coral
        REEFfitness[sortind[dep]] = self.empty_coral_fitness
        return (REEF,REEFpob,REEFfitness)

    def extremedepredation(self, REEF, REEFpob, REEFfitness, ke):
        """    
        Allow only K equal corals in the reef, the rest are eliminated.
        Input:
            - REEF: coral reef
            - REEFpob: reef population
            - REEFfitness: reef fitness
            - ke: maximum number of allowed equal corals
        Output: 
            - REEF: new coral reef
            - REEFpob: new reef population
            - REEFfitness: new reef fitness
        """

        (U, indices, count) = np.unique(REEFpob, return_index=True, return_counts=True, axis=0) 
        if len(np.where(np.sum(U, axis= 1)==0)[0]) !=0:
            zero_ind = int(np.where(np.sum(U, axis= 1)==0)[0])
            indices = np.delete(indices, zero_ind)
            count = np.delete(count, zero_ind)

        while np.where(count>ke)[0].size>0:
            higherk = np.where(count>ke)[0]
            REEF[indices[higherk]] = 0
            REEFpob[indices[higherk], :] = self.empty_coral
            REEFfitness[indices[higherk]] = self.empty_coral_fitness
            
            (U, indices, count) = np.unique(REEFpob, return_index=True, return_counts=True, axis=0) 
            if len(np.where(np.sum(U, axis= 1)==0)[0]) !=0:
                zero_ind = int(np.where(np.sum(U, axis= 1)==0)[0])
                indices = np.delete(indices, zero_ind)
                count   = np.delete(count, zero_ind)

        return (REEF,REEFpob,REEFfitness)

    def plot_results(self, Bestfitness, Meanfitness):
            import matplotlib.pyplot as plt
            
            ngen = range(self.Ngen+1)  
            fig, ax = plt.subplots()
            ax.grid(True)
            ax.plot(ngen, Bestfitness, 'b')     
            ax.plot(ngen, Meanfitness, 'r--')           
            plt.xlabel('Number of generation')
            
            if self.opt=='min': legend_place = (1,1);
            else: legend_place = (1,.3);
            plt.legend(['Best fitness', 'Mean fitness'], bbox_to_anchor=legend_place)
            
            
            titlepro = ' Problem with Length vector (L): ' + str(self.L)
            titlepar = 'Ngen: '+ str(self.Ngen)+', N: '+str(self.N)+', M: '+ str(self.M)+', Fb: '+str(self.Fb)+', Fa: '+str(self.Fa)+', Fd: '+str(self.Fd)+', Pd: '+ str(self.Pd)

            plt.title( titlepro+'\n'+ titlepar)
            
            ax.scatter(self.Ngen, Bestfitness[-1])
            ax.annotate('Best: ' + str(Bestfitness[-1]) , (self.Ngen, Bestfitness[-1]))
            
            plt.show()

    def fit(self, X=None, y=None, clf=None):
        """    
        Description: 
        Input: 
            - X: Training vectors, where n_samples is the number of samples and n_features is the number of features
            - y: Target values. Class labels must be an integer or float
            - clf: 
        Output:
            - REEF:
            - REEFpob:
            - REEFfitness:
            - ind_best:
            - Bestfitness:
            - Meanfitness:
        """ 
        
        Ngen = self.Ngen
        N = self.N
        M = self.M
        verbose = self.verbose 
        opt = self.opt
       
        #Reef initialization
        (REEF, REEFpob) = self.reefinitialization ()
        REEFfitness = self.fitness(REEFpob)

        # Store empty coral and its fitness in an attribute for later use
        empty_coral_index = np.where(REEF == 0)[0][0]
        self.empty_coral = REEFpob[empty_coral_index, :].copy()
        self.empty_coral_fitness = self.fitness(self.empty_coral.reshape((1, len(self.empty_coral))))[0]
        
        Bestfitness = []
        Meanfitness = []

        Bestfitness.append(self.opt_multiplier*np.min(REEFfitness))
        Meanfitness.append(self.opt_multiplier*np.mean(REEFfitness))
        if verbose:
            print('Reef initialization:', self.opt_multiplier*np.min(REEFfitness))


        for n in range(Ngen):
            ESlarvae = self.broadcastspawning(REEF, REEFpob)
            ISlarvae = self.brooding(REEF, REEFpob)

            # larvae fitness
            ESfitness = self.fitness(ESlarvae)
            ISfitness = self.fitness(ISlarvae)

            # Larvae setting
            larvae = np.concatenate([ESlarvae,ISlarvae])
            larvaefitness = np.concatenate([ESfitness, ISfitness])
            (REEF, REEFpob, REEFfitness) = self.larvaesettling(REEF, REEFpob, REEFfitness, larvae, larvaefitness)

            # Asexual reproduction
            (Alarvae, Afitness) = self.budding(REEF, REEFpob, REEFfitness)
            (REEF, REEFpob, REEFfitness) = self.larvaesettling(REEF, REEFpob, REEFfitness, Alarvae, Afitness)

            if n!=Ngen:
                (REEF, REEFpob, REEFfitness) = self.depredation(REEF, REEFpob, REEFfitness)    
                (REEF, REEFpob, REEFfitness) = self.extremedepredation(REEF, REEFpob, REEFfitness, int(np.round(self.ke*N*M)))

            Bestfitness.append(self.opt_multiplier*np.min(REEFfitness))
            Meanfitness.append(self.opt_multiplier*np.mean(REEFfitness))

            if all([n%10 == 0, n != Ngen, verbose]):
                print('Best-fitness:', self.opt_multiplier*np.min(REEFfitness), '\n', str(n/Ngen*100) + '% completado \n' );

        if verbose:
            print('Best-fitness:', self.opt_multiplier*np.min(REEFfitness), '\n', str(100) + '% completado \n' ) 
        ind_best = np.where(REEFfitness == np.min(REEFfitness))[0][0]

        self.plot_results(Bestfitness, Meanfitness)
        print('Best coral: ', REEFpob[ind_best, :])
        print('Best solution:', self.opt_multiplier*REEFfitness[ind_best])
        
        return (REEF, REEFpob, REEFfitness, ind_best, Bestfitness, Meanfitness)
